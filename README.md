# Google Photos Discovery Engine

A research workspace for exploring public complaints about finding photos from incomplete memories. This is an **independent course project, not affiliated with Google**. It studies the gap between remembering a photo and retrieving it; it does not search a personal photo library.

The light, Google Photos-inspired interface has four primary views: **Overview** for the main finding and saved research answers, **Patterns** for comparisons and source coverage, **Evidence** for source records, and **Research tools** for evidence Q&A and the existing complaint classifier. Methodology remains available as a reference. Existing `/analytics` and `/copilot` URLs are retained.

The web app is one FastAPI service. In production it serves the built React app and its same-origin `/api` routes. The checked-in SQLite database is a read-only research snapshot; ingestion and analysis scripts run separately and are never triggered by web startup.

## Project purpose and documentation

The research asks what people remember and forget about photos, how they search, and which retrieval patterns warrant closer investigation. The collection contains more than 10,000 feedback items, not 10,000 verified in-scope retrieval failures. All five saved research answers link to supporting records or clusters, and descriptive severity scores are not measurements of churn.

Each topic has one current reference:

| Document | Contents |
| --- | --- |
| [Project context](docs/context.md) | Problem, audience, research scope, current capabilities, and deliverable boundaries |
| [Implementation plan](docs/implementation_plan.md) | Phase-by-phase delivery status, remaining work, dependencies, and risks |
| [Architecture](docs/architecture.md) | Runtime boundaries, data model, actual API routes, design decisions, and failure behavior |
| [Methodology](docs/methodology.md) | Research questions, extraction contract, pipeline interpretation, provenance, and coursework handoff limitations |
| `docs/deployment.md` (local-only, Git-ignored) | Detailed Vercel walkthrough; shared setup essentials are below |
| [Frontend](frontend/README.md) | Routes, visual design ownership, and UI behavior |

## Local development

Use Python 3.12 and Node.js 20.19+ (or 22.12+ for Vite 8). Run commands from the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
npm ci --prefix frontend
cp backend/.env.example backend/.env
```

Start the API and Vite in two terminals:

```bash
source .venv/bin/activate
uvicorn backend.api.main:app --reload --port 8000 --env-file backend/.env
```

```bash
npm run dev --prefix frontend
```

Open `http://localhost:5173`. Vite proxies `/api` to `http://localhost:8000`; the browser uses same-origin URLs. API documentation is at `http://localhost:8000/docs`.

To test the production-style single service locally:

```bash
npm run build --prefix frontend
uvicorn backend.api.main:app --port 8000 --env-file backend/.env
```

Open `http://localhost:8000` and directly load routes such as `/analytics`, `/evidence`, and `/copilot`.

## Gemini settings

Browsing saved findings, patterns, evidence, and extractive Evidence Q&A works without a key. The Q&A endpoint (`/api/copilot`) uses Gemini to write an answer only when **both** `GEMINI_API_KEY` is set and `COPILOT_USE_GEMINI=true`. Its citations still refer to records in the SQLite snapshot. The separate, existing complaint classifier (`/api/test-search`) may use `GEMINI_API_KEY` for embedding; when that is unavailable or fails, it returns a labeled synthetic fallback. That fallback is a demonstration, not retrieved corpus evidence.

For offline ingestion, extraction, clustering, or synthesis, install the additional packages from `backend/requirements-pipeline.txt` and consult [the methodology](docs/methodology.md). Those commands can write to data files; do not run them against the checked-in snapshot unless you intend to regenerate it.

## Deployment and project layout

Deploy **this repository root** as one Vercel project, using the FastAPI preset and its `pyproject.toml` entrypoint. Leave Build Command and Output Directory overrides off; the build script in `pyproject.toml` runs `npm ci` and Vite once. FastAPI serves `frontend/dist` and `/api` on the same origin. No Render service or separate frontend project is needed. Publish the current root-level layout to the deployment branch before importing it. See the [official FastAPI deployment guide](https://vercel.com/docs/frameworks/backend/fastapi), or `docs/deployment.md` for the detailed local-only walkthrough.

```text
backend/       FastAPI routes, offline pipeline, and bundled SQLite/raw snapshot
frontend/      React UI; Vite output is served by FastAPI
docs/          Context, implementation plan, architecture, methodology; local deployment guide is ignored
```

The saved `frontend/src/data/stats.json` is a historical generated snapshot. Its 12,808 ingested, 2,405 relevant, and 690 in-scope counts differ from the current bundled database's 12,818 records, 2,447 relevant, and 691 `vague_memory_retrieval` rows (690 of those are marked relevant). The UI labels each denominator and shows the discrepancy; neither artifact is silently rewritten. See [data provenance](docs/methodology.md#data-provenance-and-caveats).

## Verification

```bash
python -m pytest backend/tests/test_api.py
npm run lint --prefix frontend
npm run build --prefix frontend
```

See [architecture](docs/architecture.md) for the data flow and API boundaries.
