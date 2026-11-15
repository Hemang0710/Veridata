# Spec 007 — Auth, multi-user, and persistence

**Status:** Ready for plan review
**Scope target:** Tier 1, the product unlock. The biggest architectural change
since the original build.

## Specify (what and why)

### Goal
Turn Veridata from a single-dataset, single-user demo into a real multi-user
app: people sign up, log in, upload datasets that persist and stay private to
them, and see their past queries. This is what makes it usable by real people
and what lets us safely add a paid model later (behind auth + rate limits).

Decisions (made):
1. **Supabase** for auth, Postgres, and file storage, one service, free tier.
2. **Per-user data isolation via Postgres Row Level Security (RLS).** A user can
   only ever read their own rows. Enforced in the database, not just the app.
3. **Uploaded data persists per user and loads into DuckDB on demand.** The
   single in-memory global dataset is removed. DuckDB stays the query engine.

### User stories
- As a new user, I can sign up and log in.
- As a logged-in user, I can upload a CSV that is saved and private to me.
- As a logged-in user, I can see my saved datasets and pick one to ask about.
- As a logged-in user, I can see my past questions and their answers.
- As a logged-out visitor, I cannot use the app or see anyone's data.

### Acceptance criteria
- A user can sign up, log in, and log out (email-based auth via Supabase).
- The app requires login; `/upload` and `/ask` reject unauthenticated requests.
- The backend verifies the Supabase JWT on every protected request and derives
  the user id from it, never from client-supplied data.
- Each upload is stored and associated with the user; one user can never read,
  query, or list another user's datasets (enforced by RLS, verified by a test).
- `/ask` runs against the authenticated user's selected dataset, loaded into
  DuckDB for that request; the single global dataset is gone.
- Query history (question, SQL, answer, confidence, timestamp) is persisted per
  user and listable.
- Per-user rate limiting on `/ask` (a sane daily cap) so a paid model can't be
  abused.
- The verification layer, charts, and traceability all still work per request.

### Out of scope (do not build here)
- Billing/payments, teams/organizations, sharing datasets between users.
- Social login (email auth only for now; magic link or password).
- Real-time collaboration.
- The frontier-model swap, paid infra, and domain (separate quick wins after this).

## Plan (how)

### Architecture
- **Frontend (Next.js + `@supabase/ssr`):** handles sign up / log in / log out
  and the session. Attaches the Supabase access token (JWT) to every backend
  request. Gates the app UI behind a session.
- **Backend (FastAPI):** a dependency verifies the Supabase JWT on each protected
  endpoint (validating it against Supabase's signing key), extracts `user_id`,
  and makes it available to the pipeline. No endpoint trusts a client-sent user id.
- **Database (Supabase Postgres):** tables for datasets and query history, each
  with a `user_id` column and RLS policies tying rows to `auth.uid()`.
- **Storage:** the uploaded CSV is stored per user (Supabase Storage, path keyed
  by user id). On `/ask`, the user's selected dataset is loaded into a DuckDB
  instance scoped to that request. Trade-off: a reload per request; acceptable at
  this scale, and cacheable later.

### Data model (Postgres)
- `datasets`: id, user_id, name, columns (json), row_count, storage_path,
  created_at. RLS: user_id = auth.uid().
- `query_runs`: id, user_id, dataset_id, question, sql, answer (json),
  confidence, abstained, created_at. RLS: user_id = auth.uid().

### Key decisions
- **RLS is the real guardrail.** Even if app code had a bug, the database refuses
  cross-user reads. Isolation enforced where the data lives, not only in app logic.
- **user_id always comes from the verified JWT**, never from the request body.
- **DuckDB stays the engine**; Supabase is storage + auth + history. The model
  still only sees schema + sample rows, now from the user's own dataset.
- Keep the pipeline web-independent: it takes a user id and a dataset handle, so
  the auth/storage layer wraps it rather than leaking into it.

## Tasks (build in slices, each reviewed and merged)
1. **Supabase setup + schema:** create the project (dashboard), the `datasets`
   and `query_runs` tables, and RLS policies tying rows to `auth.uid()`. Document
   the env vars (Supabase URL, anon key, service role key, JWT secret).
2. **Backend auth:** a FastAPI dependency that verifies the Supabase JWT and
   returns the user id; protect `/upload` and `/ask`; reject unauthenticated
   requests. Tests with a valid and an invalid/absent token.
3. **Frontend auth:** Supabase client via `@supabase/ssr`, sign up / log in /
   log out UI, gate the app behind a session, attach the token to API calls.
4. **Per-user persistence:** on `/upload`, store the CSV per user + a `datasets`
   row; remove the in-memory global. On `/ask`, load the user's selected dataset
   into DuckDB. Test that two users' data stay separate.
5. **Query history:** persist a `query_runs` row per ask; endpoints to list a
   user's datasets and past queries.
6. **Frontend data UI:** list the user's saved datasets (pick one to query) and
   show query history.
7. **Per-user rate limiting** on `/ask` (a daily cap), returning a clear message
   when exceeded.
8. **Tests + manual check:** two separate accounts prove isolation end to end;
   verification, charts, and traces still work per request.
