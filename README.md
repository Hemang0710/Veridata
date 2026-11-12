# Veridata
AI data analyst that answers plain-English questions over your CSV or database, verifies its own answers, and turns them into clear charts.

## Deploy (backend on Render)

Render root directory: `backend/` (or use the `render.yaml` Blueprint at the repo root).

- **Build command:** `pip install .`
- **Start command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

The start command binds `0.0.0.0` and Render's injected `$PORT`. Set these in the
Render dashboard (secrets never go in git):

- `LLM_PROVIDER`, `LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL` — provider config.
- `CORS_ALLOW_ORIGINS` — the deployed frontend origin (e.g. `https://<app>.vercel.app`).
  Read by `backend/app/main.py`; comma-separate multiple origins. Defaults to
  `http://localhost:3000` for local dev.

Render's free tier sleeps after ~15 min idle and wakes in ~1 min, so the first
request after a cold start is slow; subsequent requests are fast.
