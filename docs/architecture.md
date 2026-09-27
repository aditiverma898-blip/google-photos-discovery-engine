# Architecture

## Purpose and runtime boundary

The Google Photos Discovery Engine is an independent research case study about finding photos from incomplete memories. It combines a preserved feedback corpus, saved analysis, and an evidence-browsing interface. It does not connect to a user's Google Photos account.

The current stack is **React 19 + Vite 8, FastAPI, and SQLite**. One FastAPI application serves both `/api/*` and the built frontend in production. During development, Vite proxies `/api` to local Uvicorn. The browser uses relative URLs; a separate API origin, PostgreSQL service, or vector database is not required.

```text
Offline collection and analysis, in a writable environment
  Source-specific collectors
    -> backend/data/raw/**/*.jsonl
    -> extraction, relevance/category passes, embeddings, clustering, synthesis
    -> backend/data/discovery_engine.db
    -> separately generated frontend/src/data/stats.json

Read-only web application
  Browser
    -> FastAPI serves frontend/dist and SPA routes
    -> /api reads the packaged SQLite snapshot
    -> optional Gemini calls for research-tool requests only
```

No web request, startup, or cold start runs the ingestion pipeline, migrations, clustering, or synthesis regeneration. The generated JSON and database are distinct artifacts; matching some totals does not prove they are identical snapshots. [Methodology](methodology.md#data-provenance-and-caveats) is the authoritative explanation of their denominators.

## Code organization

| Path | Responsibility |
| --- | --- |
| `backend/api/main.py` | FastAPI lifecycle, API registration, read-only connection setup, and frontend serving |
| `backend/api/routes.py` | Read endpoints, evidence filtering, Evidence Q&A, and complaint classifier |
| `backend/db/connection.py` | Separate read-only web connection and writable offline connection |
| `backend/db/migrations/` | SQLite schema definitions; not executed by the web lifecycle |
| `backend/ingestion/` | Source-specific collectors and shared request, checkpoint, and text-deduplication helpers |
| `backend/extraction/` | Extraction contract, deterministic bulk processor, and record validator |
| `backend/clustering/` | Embedding generation, clustering, labeling, and descriptive metrics |
| `backend/synthesis/` | Saved-question definitions, prompt/schema, and synthesis generator |
| `backend/scripts/` | Offline orchestration, categorization, population, and diagnostics |
| `frontend/src/` | Routed research interface, shared components, and visual theme |

The offline modules reflect multiple data-generation paths. Their presence does not establish which path generated every stored field. In particular, `extraction/batch_processor.py` currently uses deterministic rules despite its filename and older comments. See [extraction and regeneration limits](methodology.md#extraction-contract-and-provenance).

## User interface and routes

| View | Route | Content and data source |
| --- | --- | --- |
| Overview | `/` | Featured saved finding, a database-backed example, compact snapshot metrics, five saved synthesis answers, pattern shares, and source caveats |
| Patterns | `/analytics` | Saved funnel, cluster comparison/ranking, and database-backed source, strategy, and workaround breakdowns |
| Evidence | `/evidence` | Paginated database records with URL-backed search and filters |
| Source record | `/evidence/:id` | Full stored source text, extracted context, and assigned cluster |
| Cluster detail | `/cluster/:id` | Saved cluster summary and current database records for that cluster |
| Research tools | `/copilot` | Evidence Q&A; `?tool=classifier` selects the complaint classifier |
| Methodology | `/methodology` | Research scope, source coverage, process, and interpretation limits |

The `/analytics` and `/copilot` URLs remain stable even though the navigation labels are Patterns and Research tools. `/funnel` redirects to `/analytics`; `/test-drive` redirects to the classifier.

The interface uses light surfaces, a finding-first Overview, readable source text, and restrained blue accents. At compact widths, Evidence keeps search visible and collapses the additional filters. All navigation and API requests remain on the app's origin; no standalone-preview server is required.

## Data model

The packaged database is `backend/data/discovery_engine.db`. The legacy `backend/data/database.db` is not the web dataset.

| Table | Principal fields and purpose |
| --- | --- |
| `feedback_records` | Stable `id`, `source_platform`, display `source`, unique `url_id`, `raw_text`, photo/memory/search/failure/workaround/emotion fields, `cluster_id`, relevance/category flags, classification metadata, embedding, and timestamps |
| `clusters` | `cluster_id`, label/description, saved count, source diversity, severity score, failure points, representative quotes, and centroid |
| `synthesis_answers` | Question ID/text, saved answer, evidence references, and generation time |
| `ingestion_log` | Source/batch tracking, counts, status, errors, and timestamps |
| `pipeline_runs` | Offline phase status, processed counts, errors, and timestamps |

Arrays and structured evidence are serialized as SQLite `TEXT`; embeddings and centroids use `BLOB`. The web classifier decodes vector blobs as float32 arrays and compares them using NumPy cosine distance. It does not query a PostgreSQL HNSW index.

`url_id` can be a source identifier rather than a usable URL. `created_at` can represent batch ingestion rather than the date of the customer's experience. Preserve missing metadata instead of inventing it.

The read-only connection uses a SQLite URI with `mode=ro`, verifies that the dataset exists, and is reused behind an async initialization lock. Offline scripts use a separate writable connection, which can load `sqlite-vec`; this is not the web query path.

## API contract

The router is implemented in [routes.py](../backend/api/routes.py). FastAPI exposes generated API documentation at `/docs`.

| Method | Path | Behavior |
| --- | --- | --- |
| GET | `/api/clusters` | Cluster metadata and database-derived counts/selected examples, ordered by stored severity |
| GET | `/api/clusters/{cluster_id}/records` | All records assigned to a cluster; this endpoint is not paginated |
| GET | `/api/coverage` | Source-labeled coverage and relevance/scope counts; its `total_corpus` sums labeled sources, not every database row |
| GET | `/api/analytics/breakdowns` | Source-by-cluster matrix, extracted strategies, and workaround groups using the explicit in-scope filter |
| GET | `/api/synthesis` | Saved database synthesis answers |
| GET | `/api/pipeline-funnel` | Legacy diagnostic combining raw-file/database reads with hard-coded processing assumptions; not the source of the UI's saved funnel |
| GET | `/api/evidence` | Paginated, filtered records plus result and corpus counts |
| GET | `/api/evidence/{record_id}` | One record and its source, extracted fields, relevance/category, and cluster name |
| POST | `/api/copilot` | `{ "question": "..." }`: cited answer or abstention |
| POST | `/api/test-search` | `{ "query": "..." }`: nearest-cluster classification and similar records, or a labeled synthetic demonstration |

`/api/evidence` accepts `page`, `limit`, `search`, `source`, `cluster_id`, `emotion`, `scope`, `search_strategy`, and `workaround_group`. Page is clamped to at least 1 and limit to 1-100. Search matches source text, failure point, or photo type. The UI requests 20 records per page.

The in-scope predicate requires both `is_retrieval_relevant = 1` and `failure_category = 'vague_memory_retrieval'`. Source, cluster, and other filters are combined with that scope. Reserved selectors include `__unattributed__` for a missing source and `__unspecified__` for a missing strategy. Workaround groups are `no_text`, `scroll_mention`, and `other_text`.

The current Patterns page reads its saved funnel directly from `stats.json`, not `/api/pipeline-funnel`. The legacy diagnostic's processing and clustering assumptions must not be treated as measured current pipeline outcomes.

## Research-tool behavior

**Evidence Q&A:** filters the existing corpus to in-scope records, matches question terms against saved text/fields, ranks candidates, and returns up to three record citations. It may include a related saved synthesis excerpt. Without adequate matches it abstains. The default answer is extractive; when both Gemini configuration switches are enabled, a wording pass may replace it. Generated citation IDs must belong to the retrieved candidates. ID validation is not a guarantee that every generated claim is entailed by its citation.

**Complaint classifier:** optionally embeds the submitted query, compares it to stored cluster centroids and record vectors, and returns distances and match status. The current distance threshold is 0.45, with a separate possible-match/data-loss boundary at 0.55. These are classifier settings, not measured probabilities. If embedding is unavailable or matching fails, the response marks `synthetic_fallback` and includes an evidence notice. The frontend distinguishes these illustrative examples from retrieved records.

The classifier does not perform the originally proposed full live extraction-and-JSON-display workflow. Research tools do not add the submitted text to the corpus or change research counts.

## Design decisions and trade-offs

| Decision | Reason and boundary |
| --- | --- |
| One service and same-origin API | Keeps local and deployed routing simple; avoids coordinating separate frontend/backend origins |
| Packaged read-only SQLite | Fits a preserved course-demo corpus and immutable serverless deployments; not a live collaborative research store |
| Offline heavy processing | Keeps ingestion, clustering, and regeneration outside web request latency and data integrity boundaries |
| Separate saved JSON and database artifacts | Preserves provenance instead of rewriting history to force agreement; requires visible source/denominator labels |
| Evidence links and abstention | Makes unsupported questions and source inspection explicit rather than returning invented research |
| Optional model wording | Browsing and extractive Q&A work without a provider key; the separate classifier fallback remains explicitly synthetic |
| Original study identity | Borrows Google Photos' light visual language without implying Google ownership or personal-photo access |

## Failure behavior and edge cases

| Condition | Current handling |
| --- | --- |
| Packaged dataset unavailable | Data endpoints return an explicit 503; the frontend shows an error rather than substituting fabricated records |
| Unknown evidence ID | API returns 404; record page shows a not-found error |
| Unknown saved cluster | Cluster page shows a not-found state; an empty record selection is not presented as a research finding |
| No matching evidence | Empty result state with a clear-filters action |
| Superseded evidence request | Frontend read effects abort their previous request during filter/route changes |
| Q&A question outside supported evidence | Abstained result with no invented citations |
| Gemini wording unavailable or unusable | Cited extractive response remains available |
| Classifier provider/matching failure | Synthetic demonstration is labeled, including simulated examples |
| Missing source or extraction fields | Explicit unavailable/not-extracted labels; no invented original-source URL |
| Clipboard denied/unavailable | Copy-link action displays failure guidance instead of reporting success |
| Wide matrices and narrow viewports | Local table scrolling, stacked sections, and compact filter controls |

These behaviors do not imply comprehensive load testing, production rate limiting, automatic PII removal, multilingual validation, or complete accessibility certification. Offline retry/checkpoint helpers also do not guarantee every script is safely resumable.

## Deployment boundary

Root `pyproject.toml` selects `backend.api.main:app` and builds `frontend/dist`. Root `vercel.json` packages the database, raw JSONL, saved stats, and built frontend inside one Python function, excluding development files. Only the built frontend is served as static content; raw files and SQLite must not be placed in a public directory.

See the [README](../README.md#deployment-and-project-layout) for shared deployment basics, `docs/deployment.md` for the local-only walkthrough when available, and [methodology](methodology.md) for research definitions and known data limitations.
