# Implementation plan and delivery status

**Last aligned with the implementation:** 2026-09-25  
**Scope reference:** [Project context](context.md)

This is a current-state delivery plan, not the original greenfield schedule. The light research interface is already applied to the real project. Remaining work below is explicitly separated from implemented functionality; listing it does not authorize changes or establish a course deadline.

**Status meanings:** Implemented = present in the current code/artifacts. Partial = supporting code or outputs exist, but an important gap remains. To verify = evidence of completion is not established here. Optional = a separate scope decision is required.

## Phase 0 - Repository and runtime

**Status: Implemented; hosted deployment still to verify.**

The repository has a React/Vite frontend, a FastAPI entrypoint, a packaged SQLite dataset, root-level dependency/deployment configuration, and separate offline pipeline dependencies.

- [x] Serve the built frontend and `/api` through one FastAPI application.
- [x] Proxy relative API requests through Vite during frontend development.
- [x] Open the packaged web database read-only without startup migrations.
- [x] Configure a single Vercel project at the repository root.
- [ ] Confirm the live hosted deployment, function bundle, and public demo URL before submission.

Preserve the one-service boundary. PostgreSQL, pgvector, a split frontend/backend deployment, and a new vector service are not required by the current design. Shared setup commands belong in the [README](../README.md); the detailed `docs/deployment.md` walkthrough is local-only and Git-ignored.

## Phase 1 - Collection and dataset preservation

**Status: Existing corpus available; collection quality and lineage partially verified.**

Source collectors and shared retry, checkpoint, and normalized-text deduplication helpers exist. Raw JSONL and the populated database are preserved. Their existence is not proof of complete source coverage, corpus-wide deduplication, or manual validation.

- [x] Keep the existing raw batches and SQLite dataset available to the project.
- [x] Expose record-level evidence and label the in-scope subset.
- [x] Document saved-snapshot/database differences rather than forcing agreement.
- [ ] Review a bounded sample across sources for relevance, duplicates, source attribution, and sensitive content before making stronger research claims or distributing more widely.
- [ ] Record artifact lineage and processing provenance if a new dataset version is produced.

**Acceptance for a future refresh:** retain the original artifacts, record the new artifact/version and generating path, report collection and in-scope counts separately, and document review findings. Do not regenerate the corpus as part of a UI or documentation update.

## Phase 2 - Extraction and relevance

**Status: Partial; full regeneration is not ready to claim as complete.**

The project contains `SYSTEM_PROMPT` and `EXTRACTION_SCHEMA`, deterministic extraction paths, validation helpers, and separate relevance/category scripts. The current `extraction/batch_processor.py` does not submit Gemini Batch API jobs.

- [x] Preserve the extraction-field contract and distinguish source text from interpretation.
- [x] Use both relevance and failure category for in-scope web queries.
- [ ] Reconcile the processor/validator contract before running `run_extraction.py`: the processor does not currently supply `is_retrieval_attempt`, which the validator expects.
- [ ] Decide and document the supported regeneration path instead of assuming every historical script forms one working pipeline.
- [ ] Add targeted extraction/validation checks and manually review accuracy if regeneration is brought into scope.

**Acceptance for regeneration:** a small, separate test dataset passes the chosen path with explicit accepted/rejected counts, required fields, provenance, and failure reporting. No fixed accuracy or language-coverage guarantee is claimed without an evaluation.

The exact definitions and limitations are in [methodology](methodology.md#extraction-contract-and-provenance); do not duplicate the schema or prompt here.

## Phase 3 - Embeddings, clustering, and metrics

**Status: Modules and saved outputs implemented; regeneration quality remains a separate task.**

The offline code includes Gemini embedding, UMAP/HDBSCAN, a silhouette-selected K-Means fallback, cluster labeling, centroid computation, and descriptive metrics. The UI reads five saved retrieval-pattern clusters and one missing-photos context cluster.

- [x] Make saved clusters, counts, severity scores, and source records explorable.
- [x] Keep all 690 in-scope items accounted for, including 48 within the context cluster.
- [x] Identify emerging/small-sample patterns and retain the original scores.
- [ ] If regenerating, check embedding compatibility and missing values, inspect cluster coherence, and preserve citation/cluster lineage.
- [ ] Validate label and severity interpretation before using the rankings as product priorities.

**Acceptance for a new analysis:** document its model/configuration and input artifact; inspect grouping and supporting quotes; distinguish full-cluster counts from in-scope counts. Do not invent a target cluster count or imply that stored severity measures churn.

## Phase 4 - Synthesis and evidence Q&A

**Status: Saved synthesis and Q&A implemented; research-quality evaluation incomplete.**

- [x] Display all five saved synthesis answers with record/cluster references.
- [x] Provide term-based Q&A over in-scope evidence with citations and abstention.
- [x] Keep extractive answers available without Gemini credentials.
- [x] Gate Gemini-written wording behind its explicit configuration switch and validate returned citation IDs against retrieved candidates.
- [ ] Review whether the cited text supports individual answer claims; existence of a valid ID is not sufficient.
- [ ] If improving answer quality, define supported/unsupported question examples and evaluate retrieval, citation relevance, and abstention.

**Acceptance for stronger quality claims:** report the evaluation sample and limitations, preserve unsupported-answer behavior, and never replace missing evidence with fabricated quotes.

## Phase 5 - API and interactive classification

**Status: Current read-only API and classifier implemented; original live-extraction feature not implemented.**

- [x] Serve coverage, clusters, synthesis, breakdowns, paginated evidence, and individual records.
- [x] Preserve stable source-record links and combined URL-backed filters.
- [x] Provide complaint-to-cluster matching and similar-record output.
- [x] Label synthetic classifier fallback and keep simulated examples separate from corpus evidence.
- [x] Keep provider credentials server-side and web requests separate from dataset mutation.
- [ ] If required by the course rubric, separately scope full live structured extraction, parsed-JSON presentation, and an in-app schema viewer.

The supported paths are listed in [architecture](architecture.md#api-contract). Do not treat proposed endpoints such as `/api/analyze` or `/api/schema` as available. The legacy `/api/pipeline-funnel` diagnostic is not the authoritative source of current processing outcomes.

## Phase 6 - Frontend and visual design

**Status: Implemented in the actual application.**

- [x] Apply the approved light design across Overview, Patterns, Evidence, record/cluster detail, Research tools, and Methodology.
- [x] Lead Overview with a qualified finding and a cited example, followed by compact metrics and saved research questions.
- [x] Use an original study mark, matching favicon/theme color, and independent-course-project attribution.
- [x] Keep existing `/analytics` and `/copilot` routes while changing their navigation labels.
- [x] Improve text readability and retain visible source, denominator, and model-output caveats.
- [x] Collapse extra Evidence filters on compact screens and provide copy-link success/failure feedback.
- [x] Build the frontend served by FastAPI; no standalone design-preview port or preview banner is part of the project.

The applied design was checked on desktop, tablet, and mobile during its integration. Broader accessibility certification and exhaustive cross-browser coverage are not implied. A broad stylesheet refactor or additional product features are separate work, not prerequisites for preserving the approved design.

## Phase 7 - Verification and hardening

**Status: Frontend build/lint and local browser checks completed during design integration; automated API tests exist.**

Local checks covered the connected routes, direct loads, same-origin links, filtering, pagination, citations, mobile controls, copy states, empty/error states, synthetic-output notices, and reduced motion. Model results were mocked for browser checks; those checks did not validate live provider quality. Data artifact hashes remained unchanged.

Use the existing verification entrypoints after relevant changes:

```bash
python -m pytest backend/tests/test_api.py
npm run lint --prefix frontend
npm run build --prefix frontend
```

These commands describe repeatable checks, not a claim that all were rerun when this document was edited.

- [ ] Before submission, repeat the applicable checks against the final build and hosted URL.
- [ ] Review keyboard-only navigation and presentation behavior in the browsers used for assessment.
- [ ] If further hardening is approved, add persistent browser regression coverage and address overlapping research-tool request behavior.
- [ ] Treat load testing, provider timeout behavior, privacy review, and a formal security audit as separate validation work; do not mark them complete from a successful demo.

## Phase 8 - Documentation, deployment, and coursework handoff

**Status: Current documentation and deployment configuration available; final submission artifacts to verify.**

- [x] Maintain one current architecture, methodology, and deployment reference.
- [x] Maintain this implementation plan and a separate current project-context document.
- [x] Remove the duplicate history folder and obsolete setup/API claims.
- [x] Document existing capabilities separately from the original brief's unfinished features.
- [ ] Verify the hosted deployment and record the final submission URL.
- [ ] Prepare or confirm the one-slide explanation and any required presentation materials.
- [ ] Check the actual course rubric for required scope, stakeholder, milestone, risk, and rationale deliverables; do not assume the app replaces them.

**Handoff acceptance:** an assessor can understand the question, trace a saved finding to source text, identify the analysis limits, and try the available tools. The author can explain what was implemented, what is synthetic or interpretive, and what remains unverified.

## Remaining-work order and dependencies

| Workstream | Order | Dependency and completion evidence |
| --- | --- | --- |
| Final course/demo handoff | First for submission | Confirm rubric and artifacts; run final local/hosted checks; record the accessible demo |
| Bounded evidence-quality review | Before stronger research claims | Review the preserved corpus without silently changing it; report limitations and any corrections requiring a new version |
| Supported offline regeneration | Only if dataset refresh is required | Fix extraction/validation alignment, verify a separate small dataset, then inspect embeddings/clusters and regenerate versioned outputs |
| Live extraction/schema viewer | Optional, rubric-dependent | Explicit scope approval, supported extraction contract, safe failure behavior, and UI/API checks |
| Broader reliability improvements | Optional | Prioritize measured problems and targeted regression tests; do not migrate infrastructure without need |

No new duration estimate, owner assignment, or deadline is assumed. Assign those against the course schedule once the remaining deliverables are confirmed.

## Delivery risks

| Risk | Current mitigation or required action |
| --- | --- |
| Snapshot totals are mistaken for one synchronized dataset | Label artifacts and denominators; preserve the documented differences |
| Repeated extracted attributes or source imbalance are presented as population facts | Keep interpretation caveats visible and conduct a bounded manual review |
| Offline scripts are assumed ready because outputs exist | Reconcile contracts and verify a small separate dataset before regeneration |
| Provider access fails during the demo | Preserve extractive Q&A, labeled classifier fallback, and visible errors |
| An older frontend build is shown | Rebuild `frontend/dist` before demonstrating the FastAPI-served application |
| Original brief requirements are mistakenly marked delivered | Keep live extraction, in-app schema presentation, hosted verification, and coursework artifacts explicitly separate |

For scope, see [context](context.md). For technical behavior, see [architecture](architecture.md); for research definitions, see [methodology](methodology.md); for shared run/deploy instructions, see the [README](../README.md). Consult `docs/deployment.md` locally for the detailed Vercel walkthrough.
