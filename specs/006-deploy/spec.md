# Spec 006 — Deploy

**Status:** Ready for plan review
**Scope target:** Make Veridata a live, shareable link.

## Specify (what and why)

### Goal
Put the app online so anyone can open it at a URL: the frontend on Vercel, the
backend on Render, talking to each other over HTTPS. This turns a local project
into a portfolio piece people can actually use.

Decisions (made):
1. **Frontend → Vercel, backend → Render.** Both have no-card free tiers (checked
   Nov 2026). Vercel is built for Next.js; Render is the best free Python host.
2. **Accept the free-tier cold start.** Render's free service sleeps after ~15
   min idle and wakes in ~1 min. Fine for a portfolio; note it in the README.
3. **Secrets live in the host's env settings, never in git.** The Groq key and
   config go in Render's environment, not the repo.

### Acceptance criteria
- The backend runs on Render at a public HTTPS URL; `/docs` and `/health` load.
- The frontend runs on Vercel at a public HTTPS URL and talks to the deployed
  backend (upload + ask work end to end on the live site).
- The Groq key and provider config are set as environment variables on Render,
  not committed anywhere.
- CORS on the backend allows the deployed frontend origin (via the existing
  env-configurable origins).
- `NEXT_PUBLIC_API_BASE_URL` on Vercel points at the Render backend URL.
- A first-time visit works after the cold-start wait; a warm visit is fast.

### Out of scope (do not build here)
- Custom domain (use the default *.vercel.app / *.onrender.com URLs).
- A paid always-on backend or keep-warm scheduler (optional later note).
- Persisting run records across restarts (Render free disk is ephemeral; the
  demo tolerates losing them).
- Multi-user data isolation (the single in-memory dataset is a known demo limit).

## Plan (how)

### Order (backend first, because the frontend needs its URL)
1. **Backend on Render.** New Web Service from the GitHub repo, root set to
   `backend/`. Start command runs uvicorn binding to Render's `$PORT`. Add env
   vars: `LLM_PROVIDER`, `LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL`, and the CORS
   allowed-origins var. Deploy, then confirm `/health` and `/docs` load at the
   Render URL.
2. **Frontend on Vercel.** Import the repo, root set to `frontend/`. Set
   `NEXT_PUBLIC_API_BASE_URL` to the Render backend URL. Deploy, get the Vercel
   URL.
3. **Close the CORS loop.** Set the backend's allowed-origins env var on Render to
   the Vercel URL, redeploy the backend.
4. **Verify end to end** on the live Vercel URL: upload `employees_test.csv`, ask
   "how many employees" (high), "average age" (abstain, no chart), "average
   salary by department" (chart).

### Prep the repo may need (small)
- A way for the backend to bind to `$PORT` and `0.0.0.0` on Render (start command
  or a small entry).
- Confirm the CORS origins are read from an env var (built in spec 004); if not,
  make them configurable.
- A `render.yaml` or documented start command, and note the build/start commands
  in the README.

### Key decisions
- Backend first so the frontend can be given a real API URL at build time.
- Nothing secret enters git; every key is set in the host dashboards.
- Keep the existing single-dataset, ephemeral-run-record behavior; document the
  limits rather than re-architecting for a demo.

## Tasks
1. Make the backend Render-ready: bind to `$PORT`/`0.0.0.0`, confirm CORS origins
   come from env, add a documented start command (and optionally `render.yaml`).
2. Deploy the backend on Render; set env vars; confirm `/health` + `/docs` live.
3. Deploy the frontend on Vercel with `NEXT_PUBLIC_API_BASE_URL` set to the
   Render URL.
4. Set the backend CORS origin to the Vercel URL; redeploy backend.
5. End-to-end check on the live site with the three probe questions; note the
   cold-start behavior.
