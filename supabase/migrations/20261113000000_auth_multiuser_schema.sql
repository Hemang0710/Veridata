-- Spec 007 — auth, multi-user, persistence.
-- Per-user tables for saved datasets and query history, isolated by Row Level
-- Security: a row is only ever readable/writable by its owner (user_id = auth.uid()).

create table datasets (
  id           uuid primary key default gen_random_uuid(),
  user_id      uuid not null references auth.users(id) on delete cascade,
  name         text not null,
  columns      jsonb not null,
  row_count    integer,
  storage_path text,
  created_at   timestamptz not null default now()
);

create table query_runs (
  id          uuid primary key default gen_random_uuid(),
  user_id     uuid not null references auth.users(id) on delete cascade,
  dataset_id  uuid references datasets(id) on delete cascade,
  question    text not null,
  sql         text,
  answer      jsonb,
  confidence  double precision,
  abstained   boolean,
  created_at  timestamptz not null default now()
);

-- RLS filters every query by user_id, so index it on both tables.
create index datasets_user_id_idx   on datasets (user_id);
create index query_runs_user_id_idx on query_runs (user_id);

alter table datasets   enable row level security;
alter table query_runs enable row level security;

-- One policy per table covers select/insert/update/delete: the row's owner only.
create policy "own datasets" on datasets for all
  using (user_id = auth.uid()) with check (user_id = auth.uid());

create policy "own query_runs" on query_runs for all
  using (user_id = auth.uid()) with check (user_id = auth.uid());
