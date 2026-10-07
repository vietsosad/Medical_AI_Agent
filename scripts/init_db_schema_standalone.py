"""One-off: apply this repo's schema (all SQLModel tables + additive columns)
to whatever database DATABASE_URL/SYNC_DATABASE_URL currently point at.

This is the exact same routine `src.main`'s lifespan already calls on every
app startup (`src.services.db.init_db_schema`) -- nothing new, just runnable
standalone so it can be pointed at a database the app itself isn't running
against yet (e.g. production, before the backend is deployed there).

Safe to run against an existing, populated database: it only ever
CREATEs a table if missing (`SQLModel.metadata.create_all`, which never
touches an existing table's structure or rows) and ADDs a column if missing
(`ALTER TABLE ... ADD COLUMN IF NOT EXISTS`, every additive column in this
codebase is nullable) -- see `_ADDITIVE_COLUMNS_BY_TABLE` in
`src/services/db.py` for the exact list. It never DROPs or ALTERs an
existing column, never deletes a row, and never touches simple_agent's own
corpus/session data -- that's `scripts/migrate_simple_agent_corpus_to_pg.py`'s
job, run separately, after this one.

Usage (DATABASE_URL/SYNC_DATABASE_URL must already be set in the
environment -- see .env.production.local for the production values):
    python scripts/init_db_schema_standalone.py --yes

Prints the target host (never the password) and requires --yes so this
can't be fired at the wrong database by a stray keypress.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path
from urllib.parse import urlsplit

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.config import get_settings  # noqa: E402
from src.services.db import init_db_schema  # noqa: E402


def _masked_target(url: str) -> str:
    parts = urlsplit(url)
    host = parts.hostname or "?"
    db = (parts.path or "").lstrip("/") or "?"
    return f"{host}/{db}"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--yes", action="store_true", help="Confirm you have checked the printed target host/db.")
    args = parser.parse_args()

    settings = get_settings()
    target = _masked_target(settings.sync_database_url or settings.database_url)
    print(f"Target database: {target}")
    if not args.yes:
        print("Re-run with --yes once you've confirmed this is the intended database.", file=sys.stderr)
        return 1

    asyncio.run(init_db_schema())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
