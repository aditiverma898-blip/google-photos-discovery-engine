# Photos research frontend

This Vite app is the interface for the Google Photos Discovery Engine. The root [README](../README.md) contains setup and deployment instructions.

For local UI development, start the FastAPI server on `127.0.0.1:8000`, then run `npm ci` and `npm run dev` here. Vite proxies `/api` to FastAPI. The production build is served by FastAPI in the single Vercel deployment.

The generated `src/data/stats.json` is a preserved pipeline snapshot. Evidence and Research tools query the read-only database through `/api`, so their totals may differ from the snapshot.

## Routes and visual design

Navigation exposes **Overview**, **Patterns** (`/analytics`), **Evidence**, and **Research tools** (`/copilot`), with Methodology as a reference. Existing record (`/evidence/:id`) and cluster (`/cluster/:id`) links remain directly loadable. All links and API calls use the same origin.

`src/index.css` supplies the base layout and `src/theme.css`, imported afterward by `src/main.jsx`, owns the light study theme, typography, and responsive overrides. `components/Shell.jsx` owns the independent-project identity and navigation. The favicon and HTML theme color match the original study mark rather than implying Google ownership.

Overview pairs a saved finding with a cited record, keeps corpus counts compact, and preserves all five saved answers. Its pattern bars use the labeled in-scope denominator. Evidence collapses extra filters on compact screens and reports copy-link success or failure. Research tools retain extractive/Gemini mode labels, citations, abstention, and synthetic-classifier notices.

Run `npm run lint` and `npm run build` here. Rebuilding is necessary for the FastAPI-served app at port 8000 to show source changes; use Vite at port 5173 for development. See [architecture](../docs/architecture.md) and [methodology](../docs/methodology.md) for the current contracts and research limitations.
