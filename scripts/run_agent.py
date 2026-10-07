"""Run the minimal data-first Deep Triage Agent in a terminal."""

from __future__ import annotations

import argparse
import logging
import os
import sys
import uuid
from pathlib import Path

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.simple_agent.agent import CorpusError, SimpleTriageAgent


def preflight(corpus_dir: str | None, index_dir: str | None) -> list[str]:
    try:
        kwargs = {}
        if corpus_dir:
            kwargs["corpus_dir"] = corpus_dir
        if index_dir:
            kwargs["index_dir"] = index_dir
        SimpleTriageAgent(
            embedder=lambda _: [0.0] * 1536,
            understanding_fn=lambda toolbox, _message: toolbox.finish_turn(intent="TRIAGE"),
            phraser=lambda kind, _context: kind,
            **kwargs,
        )
    except (CorpusError, OSError) as exc:
        return [str(exc)]
    if not os.getenv("OPENAI_API_KEY"):
        return ["OPENAI_API_KEY is not set. Add it to .env or export it in this shell."]
    return []


def print_decision(decision: dict[str, object]) -> None:
    print("[Decision]")
    print(f"- Route: {decision['route']}")
    print(f"- Concepts: {', '.join(decision['concepts']) or 'none'}")
    print(f"- Retrieval: {decision['retrieved_protocol_atoms']} protocol atoms")
    print(f"- Facts accepted: {', '.join(decision['accepted_fact_ids']) or 'none'}")
    if decision["qualitative_observation_ids"]:
        print(f"- Observations recorded: {', '.join(decision['qualitative_observation_ids'])}")
    print(f"- Action: {decision['action']} — {decision['reason']}")
    if decision['question_target_id']:
        print(f"- Next fact: {decision['question_target_id']}")


def main() -> None:
    load_dotenv(REPO_ROOT / ".env")
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--debug", action="store_true",
        help="Log every LLM call, tool call and embed call, plus a decision summary after every turn",
    )
    parser.add_argument("--check", action="store_true", help="Validate the four files, indexes and API key")
    parser.add_argument("--session-id", default=None, help="Reuse a session id for a manual multi-turn test")
    parser.add_argument("--message", default=None, help="Run one message and exit")
    parser.add_argument("--corpus-dir", default=None, help="Override the corpus directory (default: data/siu)")
    parser.add_argument("--index-dir", default=None, help="Override the embedding index directory (default: data/indexes_siu)")
    args = parser.parse_args()

    if args.debug:
        # Default level stays WARNING so third-party libraries (openai,
        # httpx, httpcore) don't dump raw HTTP traffic; only our own package
        # is turned up to DEBUG for the LLM-call / tool-call / embed trace
        # added throughout src/simple_agent/.
        logging.basicConfig(level=logging.WARNING, format="%(message)s", stream=sys.stdout)
        logging.getLogger("src.simple_agent").setLevel(logging.DEBUG)

    blockers = preflight(args.corpus_dir, args.index_dir)
    if blockers:
        print("Terminal test is not ready:", file=sys.stderr)
        for blocker in blockers:
            print(f"- {blocker}", file=sys.stderr)
        raise SystemExit(1)
    if args.check:
        print("Terminal test is ready: four corpus files, two indexes and OPENAI_API_KEY are available.")
        return

    agent_kwargs = {"enable_preask_check": True}
    if args.corpus_dir:
        agent_kwargs["corpus_dir"] = args.corpus_dir
    if args.index_dir:
        agent_kwargs["index_dir"] = args.index_dir
    agent = SimpleTriageAgent(**agent_kwargs)
    session_id = args.session_id or f"session:{uuid.uuid4().hex[:8]}"
    print("Deep Triage Agent (mock simulation). Gõ 'quit' để thoát.")
    if args.message:
        result = agent.process_turn(session_id, args.message)
        print(f"[Agent]: {result['message']}")
        if args.debug:
            print_decision(result["decision"])
        return
    while True:
        try:
            message = input("[Bệnh nhân]: ").strip()
        except (KeyboardInterrupt, EOFError):
            print()
            return
        if message.casefold() in {"quit", "exit"}:
            return
        if not message:
            continue
        result = agent.process_turn(session_id, message)
        print(f"[Agent]: {result['message']}")
        if args.debug:
            print_decision(result["decision"])


if __name__ == "__main__":
    main()
