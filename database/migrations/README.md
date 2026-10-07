# Simple-agent database bundle — setup guide

The triage agent does **not** read any local JSONL/index folder at runtime. Its
entire clinical decision corpus, and every conversation it produces, live in
PostgreSQL tables named `public.simple_agent_*`. This folder is how you get
those tables into a database that doesn't have them yet.

Two files, applied in order:

| # | File | What it is |
|---|---|---|
| 1 | `20260901_simple_agent_schema.sql` | Structure only — the 9 `simple_agent_*` tables, their btree indexes, the pgvector **HNSW** indexes, and the foreign keys to MedTriage's existing `public.users` table. No rows. |
| 2 | `20260901_simple_agent_corpus_data.sql` | Row export of the 5 **reference** tables below, taken from the dev PostgreSQL 16 + pgvector container on 2026-09-01, embeddings included. ~60 MB. |

Snapshot exported with `pg_dump` from PostgreSQL 16.14; apply with `psql` 16.x.

---

## What's in the data

The agent's behaviour is 100% driven by these five tables — it never invents a
concept, a question, or an ESI level that isn't grounded here.

| Table | Rows | Contents |
|---|---:|---|
| `simple_agent_clinical_concepts` | 1,132 | Canonical clinical concepts (chief complaints, findings, history items) with Vietnamese/English aliases, a semantic type, and a 1536-dim `text-embedding-3-small` vector for retrieval. |
| `simple_agent_concept_relations` | 4,247 | Directed edges between a concept and the fact targets / other concepts it implies — this is what lets the agent decide *which* follow-up question a complaint calls for. |
| `simple_agent_fact_targets` | 238 | The askable/observable facts (e.g. `fact_target:pain_severity`), each with a value schema, reporting style, lay-term phrasings, severity anchors, and optional `gated_by` prerequisites. |
| `simple_agent_fact_target_embeddings` | 238 | One retrieval vector per fact target, used to match a free-text patient turn onto an already-known fact before asking again. |
| `simple_agent_protocol_atoms` | 1,768 | The deterministic ESI rules. Each atom = a set of fact-target requirements + a decision effect (assign / bound an ESI level), plus its authority citation text and embedding. `decision.py` matches these in pure Python — the LLM is never in this loop. |

The schema file also creates four **runtime** tables —
`simple_agent_sessions`, `simple_agent_chat_sessions`,
`simple_agent_chat_messages`, `simple_agent_nurse_reviews` — but their rows are
**not** exported: they hold patient/nurse conversation history and reference
`users.id`. Each teammate's own sessions fill them at runtime.

---

## Prerequisites

- PostgreSQL 16 with the `pgvector` extension. The repo's `postgres` Docker
  service already satisfies this.
- The target database already has MedTriage's `public.users(id)` table (the
  schema file adds foreign keys to it).
- Stop the backend while applying, so it never reads a half-seeded corpus.

## Apply (Docker Postgres)

From the repo root:

```bash
docker compose up -d postgres

# users(id) must exist first
docker compose exec -T postgres \
  psql -U triage_user -d triage_db -v ON_ERROR_STOP=1 \
  -c "SELECT to_regclass('public.users');"        # must print: users

# 1) schema, then 2) corpus — each in one transaction, abort on any error
docker compose exec -T postgres \
  psql -U triage_user -d triage_db -v ON_ERROR_STOP=1 --single-transaction \
  < database/migrations/20260901_simple_agent_schema.sql

docker compose exec -T postgres \
  psql -U triage_user -d triage_db -v ON_ERROR_STOP=1 --single-transaction \
  < database/migrations/20260901_simple_agent_corpus_data.sql
```

Running against a non-Docker Postgres is the same `psql` command without the
`docker compose exec` wrapper.

## Verify

```bash
docker compose exec -T postgres \
  psql -U triage_user -d triage_db -P pager=off -c "
    SELECT 'clinical_concepts'      AS item, count(*) FROM simple_agent_clinical_concepts
    UNION ALL SELECT 'concept_relations',      count(*) FROM simple_agent_concept_relations
    UNION ALL SELECT 'fact_targets',           count(*) FROM simple_agent_fact_targets
    UNION ALL SELECT 'fact_target_embeddings', count(*) FROM simple_agent_fact_target_embeddings
    UNION ALL SELECT 'protocol_atoms',         count(*) FROM simple_agent_protocol_atoms
    ORDER BY item;"
```

Expected: `1132`, `4247`, `238`, `238`, `1768`. Vector shape:

```bash
docker compose exec -T postgres \
  psql -U triage_user -d triage_db \
  -c "SELECT vector_dims(embedding) FROM simple_agent_protocol_atoms LIMIT 1;"   # 1536
```

## Enable the agent

```dotenv
# .env
SIMPLE_AGENT_ENABLED=true
```

```bash
docker compose up -d --build backend
```

The agent is served under `/api/v1/simple-triage/*` and
`/api/v1/nurse-simple/*`.

## Applying to a database that already has a partial `simple_agent_*` schema

Don't replay the schema file. Start the updated backend instead —
`init_db_schema()` in `src/services/db.py` adds missing tables and columns
additively — then refresh the corpus with the idempotent script, which
upserts by natural id and checks every concept/atom has an embedding:

```bash
docker compose exec -T backend python scripts/migrate_simple_agent_corpus_to_pg.py
```

## Re-exporting this bundle

When the corpus changes and you need a fresh snapshot:

```bash
# schema
docker exec triage_postgres pg_dump -U triage_user -d triage_db \
  --schema-only --no-owner --no-privileges -t 'public.simple_agent_*'

# data — reference tables only, never the runtime/patient tables
docker exec triage_postgres pg_dump -U triage_user -d triage_db \
  --data-only --no-owner --no-privileges \
  --table=public.simple_agent_clinical_concepts \
  --table=public.simple_agent_concept_relations \
  --table=public.simple_agent_fact_targets \
  --table=public.simple_agent_fact_target_embeddings \
  --table=public.simple_agent_protocol_atoms
```

Strip the `\restrict` / `\unrestrict` lines pg_dump 16.14 adds, prepend
`CREATE EXTENSION IF NOT EXISTS vector;` to the schema file, and name the pair
with the export date.
