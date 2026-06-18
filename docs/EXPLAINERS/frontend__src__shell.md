# Explainer — `frontend/src/main.tsx`, `App.tsx`, `vite-env.d.ts`

Small scaffolding files grouped here.

- **`main.tsx`** — React entry: mounts `<App/>` into `#root` inside `StrictMode`, imports
  `index.css`.
- **`App.tsx`** — app shell with a top nav switching between the patient **Intake** view and the
  staff **Sessions & reports** view (simple `useState`, no router).
- **`vite-env.d.ts`** — TypeScript declarations for `import.meta.env` (`VITE_API_BASE`) and the
  Vite client types.
- **`index.css`** — plain hand-written styles (see ADR-0005; no Tailwind in the POC).

## Gotchas / TODOs
- Add routing (e.g. a staff `Sessions`/report view) when those pages land (Phase G+).
