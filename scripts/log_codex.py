#!/usr/bin/env python3
"""Extract explicit user prompts from local Codex session transcripts.

Codex runtimes do not consistently invoke repository-local hook definitions.
This scanner is therefore run by the repository's Git pre-push hook. It reads
only local session transcripts, filters them to the current repository, and
records exact user requests in the common AI-log format.
"""
import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path


VN_TZ = timezone(timedelta(hours=7))
CODEX_SESSIONS_DIR = Path.home() / ".codex" / "sessions"


def git(*args: str) -> str:
    try:
        return subprocess.check_output(
            ["git", *args], text=True, stderr=subprocess.DEVNULL
        ).strip()
    except Exception:
        return ""


def parse_timestamp(value: object) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def extract_prompt(content: object) -> str:
    """Keep the user's request while discarding Codex-injected context blocks."""
    if not isinstance(content, list):
        return ""
    text = "\n".join(
        block.get("text", "")
        for block in content
        if isinstance(block, dict) and block.get("type") == "input_text"
    ).strip()
    if not text:
        return ""
    marker = "## My request:"
    if marker in text:
        return text.split(marker, 1)[1].strip()
    if text.startswith(
        ("<recommended_plugins>", "# AGENTS.md instructions", "<environment_context>")
    ):
        return ""
    return text


def session_matches_repo(transcript: Path, repo_root: str) -> bool:
    """Match only transcripts that include the current repository path."""
    try:
        with transcript.open(encoding="utf-8") as handle:
            return any(repo_root in line for line in handle)
    except OSError:
        return False


def logged_ids(log_dir: Path) -> set[str]:
    """Read IDs from pending and archived logs so repeated pushes stay idempotent."""
    candidates = [log_dir / "session.jsonl", *sorted((log_dir / "archive").glob("*.jsonl"))]
    ids: set[str] = set()
    for log_file in candidates:
        if not log_file.exists():
            continue
        with log_file.open(encoding="utf-8-sig") as handle:
            for line in handle:
                try:
                    entry_id = json.loads(line).get("entry_id")
                except json.JSONDecodeError:
                    continue
                if isinstance(entry_id, str):
                    ids.add(entry_id)
    return ids


def collect_entries(hours: int | None, repo_root: str, seen_ids: set[str]) -> list[dict]:
    if not CODEX_SESSIONS_DIR.exists():
        return []
    cutoff = None if hours is None else datetime.now(timezone.utc) - timedelta(hours=hours)
    repo = git("remote", "get-url", "origin").rstrip("/").split("/")[-1].removesuffix(".git")
    branch = git("rev-parse", "--abbrev-ref", "HEAD")
    commit = git("rev-parse", "--short", "HEAD")
    student = git("config", "user.email") or os.environ.get("USER", "unknown")
    entries: list[dict] = []

    for transcript in CODEX_SESSIONS_DIR.rglob("*.jsonl"):
        if not session_matches_repo(transcript, repo_root):
            continue
        try:
            lines = transcript.read_text(encoding="utf-8").splitlines()
        except OSError:
            continue
        for line_number, line in enumerate(lines, start=1):
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            timestamp = parse_timestamp(item.get("timestamp"))
            if cutoff and timestamp and timestamp < cutoff:
                continue
            payload = item.get("payload", {})
            if (
                item.get("type") != "response_item"
                or payload.get("type") != "message"
                or payload.get("role") != "user"
            ):
                continue
            prompt = extract_prompt(payload.get("content"))
            if len(prompt) < 2:
                continue
            entry_id = f"codex-{transcript.stem}-{line_number:06d}"
            if entry_id in seen_ids:
                continue
            entries.append(
                {
                    "ts": timestamp.astimezone(VN_TZ).isoformat()
                    if timestamp
                    else datetime.now(VN_TZ).isoformat(),
                    "tool": "codex",
                    "event": "UserPrompt",
                    "entry_id": entry_id,
                    "session_id": transcript.stem,
                    "model": "",
                    "repo": repo or Path(repo_root).name,
                    "branch": branch,
                    "commit": commit,
                    "student": student,
                    "prompt": prompt[:1000],
                    "response_summary": "",
                }
            )
            seen_ids.add(entry_id)
    return entries


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Collect Codex prompts for the current repository."
    )
    parser.add_argument(
        "--hours", type=int, default=24, help="Lookback window in hours (default: 24)."
    )
    parser.add_argument("--all", action="store_true", help="Scan all local Codex sessions.")
    parser.add_argument(
        "--dry-run", action="store_true", help="Preview entries without writing a log."
    )
    args = parser.parse_args()

    repo_root = str(Path.cwd().resolve())
    log_dir = Path(os.environ.get("AI_LOG_DIR", ".ai-log"))
    entries = collect_entries(
        None if args.all else args.hours, repo_root, logged_ids(log_dir)
    )
    if args.dry_run:
        print(f"[codex-log] Would record {len(entries)} prompt(s).")
        for entry in entries:
            preview = entry["prompt"].replace(chr(10), " ")[:120]
            print(f"  {entry['entry_id']}: {preview}")
        return
    if not entries:
        print("[codex-log] No new Codex prompts.", file=sys.stderr)
        return
    log_dir.mkdir(exist_ok=True)
    with (log_dir / "session.jsonl").open("a", encoding="utf-8") as handle:
        for entry in entries:
            handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
    print(f"[codex-log] Logged {len(entries)} prompt(s).", file=sys.stderr)


if __name__ == "__main__":
    main()
