# Veridata frontend

Next.js (App Router) + TypeScript web UI for Veridata. A thin client over the
backend API — it renders what the API returns and holds no business logic.

Spec 004 task 1 is the scaffold only; the upload/ask UI (UploadPanel,
QuestionBox, AnswerCard, ConfidenceBadge, ShowYourWork) lands in later tasks.

## Prerequisites

- Node.js 22+ and npm
- The backend running locally (see `../backend`), by default on
  `http://localhost:8000`

## Run locally

```bash
cd frontend
npm install

# Point the app at your backend. Copy the example and edit if your backend
# isn't on http://localhost:8000.
cp .env.local.example .env.local

npm run dev
```

The app starts on http://localhost:3000.

## Configuration

The backend base URL is read from the `NEXT_PUBLIC_API_BASE_URL` environment
variable (see `.env.local.example`). It falls back to `http://localhost:8000`
when unset. Because it's a `NEXT_PUBLIC_` var it is inlined at build time, so set
it before `npm run build` when deploying (e.g. as a Vercel environment variable).

## Build

```bash
npm run build   # production build (what Vercel runs)
npm run lint     # eslint (next/core-web-vitals)
```
