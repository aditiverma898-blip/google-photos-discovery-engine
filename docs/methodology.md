# Methodology

## Research question and sources

The project studies frustration when people know a photo exists but cannot retrieve it from incomplete memory. It collects public Google Photos commentary from app stores, YouTube, Reddit, and the Google Support Community. The corpus also contains comments about missing photos, synchronization, and unrelated issues; those are retained for auditability and separated from the narrow vague-memory question.

This is an independent course case study, not a representative survey, a Google-owned product, or a personal-photo search implementation. The large collection supports discovery; it does not establish how common a problem is across all Google Photos users.

The five saved research questions concern:

1. What kinds of old photos people struggle to retrieve.
2. What information people remember about a photo.
3. What information they have forgotten.
4. How people formulate searches when memory is incomplete.
5. Which in-scope clusters show stronger frustration signals.

The original brief also asked about churn. Neither complaint counts nor extracted emotions measure churn or prove causation. The fifth question should be interpreted as directional prioritization, not a demonstrated impact on retention.

## Artifacts and pipeline

Raw JSONL files in `backend/data/raw/` are collection material. SQLite `feedback_records` holds source text, extracted fields, relevance/category, and cluster assignment. `clusters` and `synthesis_answers` hold saved metadata and findings. `frontend/src/data/stats.json` is a separately generated summary snapshot. No page view or API request regenerates these artifacts.

| Stage | Current interpretation |
| --- | --- |
| Collection | Source-specific collectors save public feedback in dated JSONL batches. Shared helpers include short-text checks, normalized-text SHA-256 deduplication in a hash set, request retry/backoff, and checkpoints. These are not proof of corpus-wide uniqueness or representative sampling. |
| Extraction | The schema defines the intended fields; the current bulk processor uses deterministic rules. Additional generation/population scripts exist. A stored field alone does not identify which processing path generated it. |
| Relevance | A saved relevance pass marks retrieval-related commentary. This is separate from cluster membership and failure category. |
| Scope | Relevant records are categorized as `vague_memory_retrieval`, `data_loss_sync`, or `none_other`. A category from an earlier pass can remain on an irrelevant row. |
| Clustering | Offline modules provide embeddings, UMAP/HDBSCAN and a silhouette-selected K-Means fallback, labels, and descriptive metrics. The interface reads their saved outputs; it does not rerun clustering. |
| Synthesis | Saved answers retain cluster/record references and quotes. The interface presents them as preserved analysis, not fresh evidence generated on each visit. |

The offline [embedder](../backend/clustering/embedder.py) uses failure point and search strategy as input. [Cluster metrics](../backend/clustering/metrics.py) include source diversity, common failure points, quotes, and a severity proxy. Its component weights are 40% extracted emotion, 30% giving-up workaround text, 20% relative cluster frequency, and 10% source diversity. This describes the helper's computation, not verified lineage for every saved score. The UI preserves existing scores without recalculating them.

## Extraction contract and provenance

The exact extraction prompt and schema live in [extraction/schema.py](../backend/extraction/schema.py), under `SYSTEM_PROMPT` and `EXTRACTION_SCHEMA`. Link to those definitions rather than maintaining another copy of their enums and prompt in documentation.

| Field | Meaning |
| --- | --- |
| `is_retrieval_attempt` | Intended extraction-level indication of a specific attempt; not a substitute for the database's later relevance/category flags |
| `source_platform`, `source`, `url_id` | Origin, display source label, and source URL or identifier |
| `raw_text` | Stored source text, distinct from the interpretations below |
| `photo_type` | Interpreted media category, such as a document, screenshot, or vacation photo |
| `remembered_attributes` | Cues the person appears to recall |
| `forgotten_attributes` | Metadata or other attributes the person appears to lack |
| `search_strategy` | Interpreted search approach |
| `failure_point` | Extracted description of the failure |
| `workaround` | Recorded alternative action, if any |
| `emotional_signal` | Interpreted emotional tone, not directly observed intensity |

The prompt asks for a specific retrieval attempt, detailed remembered/forgotten cues, and no invented attributes. That instruction is not an accuracy guarantee. Empty or generic fields, ambiguous intent, sarcasm, multiple issues in one comment, and source bias require manual review. The language and short-text rules do not establish validated multilingual coverage.

The current [batch processor](../backend/extraction/batch_processor.py) is deterministic, not a working Gemini Batch API submission/polling system. The standalone [deterministic pipeline](../backend/scripts/run_deterministic_pipeline.py) is another writable path. The [validator](../backend/extraction/validator.py) checks the retrieval-attempt flag and required field presence; it is not comprehensive type/enum validation. In particular, the current bulk processor does not supply the flag expected by the `run_extraction.py` validation step, so that path needs reconciliation before regeneration. This documentation update does not fix or rerun those scripts.

The exact synthesis questions, prompt, and output schema are in [synthesis/synthesizer.py](../backend/synthesis/synthesizer.py). Source quotes and citations should be reviewed against stored records; a plausible cluster label is not proof of a particular Google Photos implementation defect.

## Data provenance and caveats

| Metric | Saved `stats.json` | Bundled database |
| --- | --- | --- |
| Total collected/stored items | 12,808 | 12,818 |
| Relevant items | 2,405 | 2,447 |
| Relevant vague-memory retrieval | 690 | 690 |
| All rows tagged `vague_memory_retrieval` | Not a separate snapshot metric | 691, including one marked irrelevant |
| Source-labeled rows | Source counts sum to 12,808 | 12,808; 10 additional rows lack a source label |

The source-labeled aggregate match does not establish record-by-record equivalence. Relevance counts differ, and the artifacts have not been reconciled; do not edit data simply to force agreement.

In the database, the 2,447 relevant rows comprise 690 vague-memory rows, 1,715 data-loss/sync rows, and 42 `none_other` rows. Another 10,371 rows are marked irrelevant. Thus the project has more than 10,000 collected items, not more than 10,000 validated in-scope complaints.

Play Store contributes 9,138 labeled records, approximately 71% of the labeled collection. The other saved source counts are YouTube Comment 3,013, Reddit 469, App Store 170, and Google Support Community 18. Source-specific collection methods, repeated content, automatic labeling, and snapshot drift limit generalization.

`url_id` may be an internal source identifier rather than a resolvable permalink. A source label alone is not independent verification of authenticity. The stored `created_at` values largely reflect ingestion batches; do not use them as a customer-behavior timeline.

Remembered-attribute frequency is not a headline metric because 487 of the 690 in-scope records share the same stored value. Extracted fields should not be treated as hundreds of independently verified observations without a quality audit.

## Read-only dashboard breakdowns

Overview's main finding, corpus strip, pattern shares, and saved answers come from `stats.json`; its cited source examples are fetched by ID from the database. The five retrieval-pattern clusters contain 642 of 690 in-scope items, with the remaining 48 assigned to the Missing Photos and Albums context cluster. All 690 remain accounted for.

Overview bars use 690 as the common denominator. Patterns' saved cluster-comparison bars show relative count, normalized to the largest cluster, with explicit counts. Its source-by-cluster matrix, strategy counts, and workaround groups query the database with **both** `is_retrieval_relevant = 1` and `failure_category = 'vague_memory_retrieval'`. Each database breakdown labels its denominator and links to matching evidence filters.

Workaround grouping uses the stored text: blank, `none`, or `None reported` becomes **no text recorded**; remaining text containing "scroll" becomes **scrolling mentioned**; other responses form the third group. Missing text does not prove that no workaround was attempted. Search strategies and emotional signals are also interpretations, not observed behavior.

A cluster's full record count must not be presented as its validated in-scope count. Severity is a descriptive stored score, not confidence, probability, prevalence, or an approved product priority.

## Research tools and evidence boundaries

Evidence Q&A (`/api/copilot`) uses term matching within in-scope records, returns citations, and abstains when support is insufficient. It defaults to an extractive answer; Gemini wording is opt-in. A valid citation ID establishes that the record exists, not that every statement is supported by that record.

The complaint classifier (`/api/test-search`) is a separate nearest-cluster/vector-matching demonstration. It can return a labeled synthetic fallback when model access or matching is unavailable. Simulated examples must never be added to the research denominator or presented as retrieved source complaints. Neither tool updates the corpus.

## Coursework handoff

The original brief requested a queryable collection, five supported research answers, a ranked cluster view, an interactive complaint test, extraction-prompt/schema transparency, and a one-slide explanation. The current deliverable maps to those goals as follows:

| Goal | Current delivery and boundary |
| --- | --- |
| Large feedback collection | Preserved raw material and queryable database; only the explicitly labeled subset is in scope |
| Five research answers | Saved answers and citations on Overview; inspect supporting records before treating conclusions as validated |
| Ranked failure patterns | Patterns and cluster detail pages, with source evidence and existing scores |
| Interactive testing | Complaint matching and Evidence Q&A; not full live extraction with parsed JSON displayed |
| Prompt/schema transparency | Linked source definitions above; there is no dedicated in-app extraction-schema viewer |
| Explanation slide | A separate coursework deliverable; the app does not generate a slide |

Do not infer completion of human quality audits, multilingual evaluation, performance targets, or coursework artifacts from old checklists. A useful presentation distinguishes the question, collection, structured interpretations, saved findings, evidence, and limitations rather than presenting the pipeline as uniformly model-generated or fully validated.

For runtime contracts and failures, see [architecture](architecture.md). For running the preserved snapshot, see the [README](../README.md#local-development); the detailed `docs/deployment.md` guide is local-only and Git-ignored.
