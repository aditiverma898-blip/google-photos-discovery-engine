# Project context

**Project:** Google Photos Discovery Engine  
**Interface identity:** Discovery study | Google Photos  
**Last aligned with the implementation:** 2026-09-25

This is the current product brief and scope reference for an independent course project. It is not a claim of employment at, affiliation with, or endorsement by Google. See the [implementation plan](implementation_plan.md) for delivery status and remaining work.

## 1. Problem and motivation

People may remember that a photo exists without remembering the date, location, filename, or album needed to find it. They may instead recall an object in the background, an event, a relative time, or a visual quality.

The project explores public feedback about these retrieval difficulties. Its purpose is to help a researcher move from a reported problem to a pattern, inspect the supporting source records, and form a hypothesis worth investigating.

The application is a research workspace, not an improved photo-search engine. It searches feedback records and classifies complaints; it does not connect to Google Photos or retrieve images from a person's library.

## 2. Audience and intended use

| Audience | Task supported |
| --- | --- |
| Researcher or PM | Compare retrieval-failure patterns and inspect evidence before proposing an opportunity |
| Course assessor | Understand the research question, examine the method and limitations, and try the interactive tools |
| Project author | Present the case study, explain decisions, and distinguish findings from assumptions |

The main presentation flow is **Overview -> Patterns -> Evidence -> source record**, with Research tools available for questions and complaint-matching demonstrations. Methodology explains how to interpret the results.

## 3. Research questions

The saved synthesis addresses five questions:

1. What kinds of old photos do users struggle to retrieve?
2. What information do people actually remember about a photo?
3. What information have they forgotten?
4. How do users formulate searches when their memory is incomplete?
5. Which in-scope clusters show the strongest frustration signals?

The original brief mentioned churn. The available complaints and severity scores do not measure churn or establish causation. The fifth question is a directional research question, not a demonstrated retention outcome.

## 4. Data and research boundary

The preserved collection includes Play Store and App Store reviews, YouTube comments, Reddit posts/comments, and Google Support Community material. The five source labels are not equally represented; app-store feedback dominates.

| Artifact | Current meaning |
| --- | --- |
| `backend/data/raw/` | Preserved source batches in JSONL format |
| `backend/data/discovery_engine.db` | Packaged SQLite research dataset: 12,818 feedback records, 2,447 marked relevant |
| `frontend/src/data/stats.json` | Separate generated snapshot: 12,808 collected items, 2,405 relevant items, 690 in scope |
| Relevant vague-memory subset | 690 database records satisfying both relevance and `vague_memory_retrieval` category |

The original collection target was approximately 10,000-12,000 items. The stored volume exceeds 10,000, but these are **collected feedback items**, not 10,000 independently validated retrieval failures.

**Primary scope:** finding an existing photo from incomplete memory.  
**Context retained:** missing photos, synchronization, backup, and other feedback, explicitly separated from the primary scope.

The five saved retrieval-pattern clusters contain 642 in-scope records; another 48 in-scope records sit within the missing-photos context cluster. A cluster name alone is not a scope filter.

The saved JSON and database must remain separately identifiable. Do not overwrite either artifact to force matching totals. See [methodology](methodology.md#data-provenance-and-caveats) for the full reconciliation caveats, source mix, and limits of extracted attributes.

## 5. Current application

| Surface | Current capability |
| --- | --- |
| Overview (`/`) | A featured saved finding beside a cited complaint, compact corpus metrics, pattern shares, all five saved answers, and interpretation caveats |
| Patterns (`/analytics`) | Saved collection/funnel counts, cluster comparison and ranking, plus database-backed source, strategy, and workaround breakdowns |
| Evidence (`/evidence`) | Search, combined filters, pagination, shareable views, and copy-link feedback |
| Record and cluster detail | Direct links to complete source text, extracted context, assigned grouping, and associated records |
| Research tools (`/copilot`) | Evidence Q&A and a separate complaint classifier selected with `?tool=classifier` |
| Methodology (`/methodology`) | Research question, collection, analysis flow, and limitations |

The approved visual direction is a **light, evidence-first research workspace** inspired by Google Photos' calm surfaces and rounded controls. It uses an original study mark, restrained blue accents, readable text, and an independent-project qualifier. On compact screens, navigation adapts and additional Evidence filters collapse.

This design is applied to the actual project, not only a standalone preview. Route names remain stable: the labels Patterns and Research tools do not rename `/analytics` and `/copilot`.

## 6. Technical and AI boundaries

The current implementation uses React 19 with Vite 8, FastAPI, and SQLite. One FastAPI service serves the built client and same-origin `/api` routes. Vite proxies API requests during local frontend development. The configured deployment target is one root-level Vercel project.

Web access to the research database is read-only. Collection, extraction, categorization, clustering, and synthesis scripts belong to offline processing in a writable environment; they are not triggered by browsing or startup.

**Evidence Q&A** retrieves in-scope records using term matching and returns cited extractive answers or abstains. Gemini-written wording is optional and requires both `GEMINI_API_KEY` and `COPILOT_USE_GEMINI=true`. A valid citation ID does not by itself prove that every answer claim is supported.

**Complaint classification** may use Gemini embedding and compare against saved vectors and centroids. If model access or matching is unavailable, it returns an explicitly labeled synthetic demonstration. It does not perform full live extraction with a parsed JSON display, and submitted complaints are not added to the corpus.

The extraction prompt/schema exist, but the current bulk processor uses deterministic rules rather than Gemini Batch API jobs. Its contract does not yet align with the flag expected by the extraction validator. Full regeneration must not be represented as a verified end-to-end workflow. The [methodology](methodology.md#extraction-contract-and-provenance) documents this limitation; [architecture](architecture.md) describes the actual modules and API.

## 7. Deliverables and acceptance boundaries

| Deliverable | Present state |
| --- | --- |
| Large, queryable feedback collection | Available as preserved raw batches and a read-only database, with scope and denominator qualifications |
| Five evidence-linked research answers | Available as saved synthesis; independent claim/quote review remains important |
| Explorable pattern ranking | Available with stored scores, small-sample caveats, and record drill-down |
| Interactive testing | Q&A and complaint matching are available; the original full live-extraction workflow is not implemented |
| Prompt/schema transparency | Definitions are linked from Methodology; no dedicated in-app schema viewer exists |
| Local demo | The built application is served by FastAPI at port 8000; Vite development uses port 5173 |
| Hosted submission | Single-service Vercel configuration exists; a live deployment and deployment verification are not established by this document |
| One-slide explanation | Separate coursework deliverable; completion must be confirmed by the author |

The research should be understandable without using the AI tools. Counts must identify their artifact and denominator, citations must lead to records, and insufficient or synthetic evidence must remain visible.

## 8. Non-goals and working constraints

- No personal Google Photos account integration, image uploads, or actual photo-library search.
- No new authentication, collaboration, real-time ingestion, or infrastructure migration simply to complete the visual presentation.
- No treating extracted emotions, cluster scores, or convenience-sample counts as measured user prevalence, confidence, or churn.
- No rewriting raw data or analysis snapshots during UI/documentation changes.
- No hiding Gemini use or synthetic fallback to make the interface appear non-AI.
- No assuming that model calls, offline regeneration, deployment, or additional features are authorized by a documentation task.

Use [architecture](architecture.md) for system behavior, [methodology](methodology.md) for evidence interpretation, the [README](../README.md) for shared run/deploy basics, and [implementation plan](implementation_plan.md) for completed phases and proposed next work. The detailed `docs/deployment.md` walkthrough is local-only and Git-ignored.
