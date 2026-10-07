# Deep Agent live conversational audit

A full audit of the MedTriage Deep Agent conducted against the **running
system**: the real FastAPI application, the real local PostgreSQL database, the
real pgvector corpora, the real OpenAI provider and the real DeepAgent runtime.
Nothing clinical was mocked.

**Read these in order. A future agent can continue this work without repeating
the audit.**

| Document | Question it answers |
|---|---|
| [`RUNTIME_MAP.md`](RUNTIME_MAP.md) | What actually runs on one patient turn, with observed cost and latency |
| [`STATE_OWNERSHIP.md`](STATE_OWNERSHIP.md) | Where every piece of conversational state lives, and which had competing writers |
| [`LLM_CONTEXT_MAP.md`](LLM_CONTEXT_MAP.md) | Exactly what each of the six LLM call sites receives — and why the agent *looked* like it forgot |
| [`QUESTION_LIFECYCLE.md`](QUESTION_LIFECYCLE.md) | A question's semantic identity, how an answer binds to it, when it may be re-asked |
| [`HARD_CODE_INVENTORY.md`](HARD_CODE_INVENTORY.md) | Every hard-coded table/ordering/budget, classified; what is a safety invariant and what was a questionnaire |
| [`FAILURE_MATRIX.md`](FAILURE_MATRIX.md) | **24 defects**, each with root cause, live transcript, fix and regression test |
| [`LIVE_E2E_RESULTS.md`](LIVE_E2E_RESULTS.md) | The 24-scenario suite: before/after metrics, full transcripts, retrieval, database, auth |
| [`NATURALNESS_EVAL.md`](NATURALNESS_EVAL.md) | How conversational quality was scored, and the limits of that signal |
| [`REFACTOR_PLAN.md`](REFACTOR_PLAN.md) | What was changed in phases A–G, what was deliberately not, and what to do next |

## Reproducing it

```bash
# the golden live suite (real LLM, real DB, real corpora)
.venv/bin/python eval/live_audit/run_audit.py --budget 25 --concurrency 3 \
    --out eval/conversations/after --summary eval/conversations/after/_summary.json

# deterministic metrics + blind naturalness judge
.venv/bin/python eval/live_audit/run_evaluation.py \
    --dir eval/conversations/after --out eval/conversations/_metrics_after.json --judge

# how the retrieval query improves as facts accumulate (§21)
.venv/bin/python eval/live_audit/retrieval_probe.py --retrieve

# what each LLM call site receives (§6)
.venv/bin/python eval/live_audit/capture_context.py

# auth restoration check — must pass before any release
.venv/bin/python eval/live_audit/auth_regression.py

# remove only the audit's own tagged rows
.venv/bin/python eval/live_audit/cleanup.py            # dry run
.venv/bin/python eval/live_audit/cleanup.py --apply
```

Regression tests for every defect: `tests/test_agents/test_live_audit_regressions.py`.

## The one-line summary

The models were never the problem. Every LLM call site received consistent,
well-scoped context throughout. What was broken was the **state around them** —
a confirmation three layers could clear, an open question the router threw away,
an accent fold that invented a symptom, and a completion path that could not
reach the reasoner. Fixing the state, not the prompts, took the suite from
**0%** of normal cases reaching a grounded ESI to **33%**, duplicate questions
from **49%** to **9.5%**, and the confirmation deadlock from **14 of 24
conversations** to **none**.
