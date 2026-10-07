"""Run the database-only Simple Agent evaluation against the live backend."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from .simple_runtime.auth import cleanup_run, create_eval_profile, ensure_eval_identity
from .simple_runtime.backend_client import SimpleAgentBackendClient
from .simple_runtime.corpus_reader import load_postgres_corpus, row_fingerprint
from .simple_runtime.deterministic_metrics import compute_metrics
from .simple_runtime.extractor import extract
from .simple_runtime.ragas_evaluator import RagasConfig, ragas_version, run_ragas
from .simple_runtime.report import RESULTS_DIR, write_snapshot
from .simple_runtime.schemas import GoldenCase

DEFAULT_CASES = Path("eval/cases/simple_agent_golden_30.jsonl")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_cases(path: Path) -> list[GoldenCase]:
    if not path.exists():
        raise RuntimeError(
            "Golden dataset not found: "
            "Generate it with python -m eval.build_golden_from_postgres."
        )
    cases = [
        GoldenCase.model_validate_json(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    # The canonical benchmark keeps its exact published shape: 30 cases, two
    # smoke cases. Its numbers are quoted in the project documents, so a file
    # that has silently grown or shrunk is a defect, not a new dataset.
    if path.resolve() == DEFAULT_CASES.resolve():
        if len(cases) != 30 or sum(case.smoke for case in cases) != 2:
            raise RuntimeError("Golden dataset must contain 30 cases and exactly two smoke cases.")
        return cases
    # Any other dataset passed through --cases (for example the expanded set
    # built by eval/build_golden_expanded.py) is validated on the properties the
    # runner actually depends on, rather than on a fixed size: there must be
    # cases to run, and at least one smoke case, because the smoke gate is what
    # stops a broken backend from burning a whole run.
    if not cases:
        raise RuntimeError(f"Golden dataset is empty: {path}")
    if not any(case.smoke for case in cases):
        raise RuntimeError(f"Golden dataset has no smoke case: {path}")
    return cases


def _preflight(path: Path, cases: list[GoldenCase]) -> dict[str, Any]:
    manifest_path = path.with_suffix(".manifest.json")
    if not manifest_path.exists():
        raise RuntimeError(f"Missing dataset manifest: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("dataset_sha256") != _sha256(path):
        raise RuntimeError("Golden dataset checksum differs from its manifest; regenerate the dataset.")
    corpus = load_postgres_corpus()
    for case in cases:
        provenance = case.postgres_provenance
        atom_id = provenance.get("protocol_atom_id")
        if atom_id and (
            atom_id not in corpus.atoms
            or provenance.get("atom_fingerprint")
            != row_fingerprint({key: value for key, value in corpus.atoms[atom_id].items() if key != "embedding"})
        ):
            raise RuntimeError(f"Selected protocol atom drifted or is missing: {atom_id}")
        for fact_id, fingerprint in provenance.get("fact_target_fingerprints", {}).items():
            if fact_id not in corpus.facts or row_fingerprint(corpus.facts[fact_id]) != fingerprint:
                raise RuntimeError(f"Selected fact target drifted or is missing: {fact_id}")
    return {
        "table_counts": corpus.table_counts,
        "table_fingerprints": corpus.table_fingerprints,
        "dataset_sha256": manifest["dataset_sha256"],
        "corpus_drift_warning": corpus.table_fingerprints != manifest.get("table_fingerprints"),
    }


def _git_sha() -> str | None:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], text=True, stderr=subprocess.DEVNULL
        ).strip()
    except Exception:
        return None


def _run_one_case(
    case: GoldenCase,
    client: SimpleAgentBackendClient,
    identity: Any,
) -> tuple[str, str | None, dict[str, Any]]:
    profile_id = create_eval_profile(identity, case.profile, case_id=case.case_id)
    result = client.run_case(case, profile_id)
    return profile_id, result.session_id, extract(case, result).model_dump()


def _run_cases(
    cases: list[GoldenCase],
    client: SimpleAgentBackendClient,
    identity: Any,
    session_ids: list[str],
    profile_ids: list[str],
    concurrency: int = 1,
) -> list[dict[str, Any]]:
    """Run every case and return one observation per case, in input order.

    ``concurrency=1`` is the historical behaviour, kept byte-for-byte: strictly
    sequential, five seconds between cases.

    Higher values exist because a case is mostly spent waiting on the model, and
    a case that walks its full question budget takes minutes. Measured on this
    repo, one case averages roughly five minutes, which puts a 300-case dataset
    at about a day of wall time run sequentially -- long enough that nobody runs
    it, which makes the dataset worthless no matter how good it is. The work is
    I/O-bound and every case owns its own EHR profile and its own conversation,
    so they do not interact; ``httpx.Client`` is safe to share across threads.

    Order is preserved regardless of completion order, so two runs over the same
    dataset produce comparable artifacts.
    """
    if concurrency <= 1:
        observations: list[dict[str, Any]] = []
        for index, case in enumerate(cases):
            if index:
                time.sleep(5.0)
            profile_id, session_id, observation = _run_one_case(case, client, identity)
            profile_ids.append(profile_id)
            if session_id:
                session_ids.append(session_id)
            observations.append(observation)
        return observations

    results: list[dict[str, Any] | None] = [None] * len(cases)
    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        futures = {}
        for index, case in enumerate(cases):
            # Stagger the launches so a burst of identical requests does not hit
            # the model provider's rate limit in the same instant.
            if index and index % concurrency == 0:
                time.sleep(1.0)
            futures[pool.submit(_run_one_case, case, client, identity)] = index
        for future in as_completed(futures):
            index = futures[future]
            profile_id, session_id, observation = future.result()
            profile_ids.append(profile_id)
            if session_id:
                session_ids.append(session_id)
            results[index] = observation
    return [item for item in results if item is not None]


def _smoke_failed(observations: list[dict[str, Any]]) -> bool:
    for observation in observations:
        expected_esi = observation.get("expected_esi")
        if (
            observation.get("backend_error")
            or not observation.get("terminal")
            or observation.get("predicted_esi") != expected_esi
            or not observation.get("passed")
            or observation.get("safety_violations")
        ):
            return True
    return False


def _current_observations() -> list[dict[str, Any]]:
    observed_path = RESULTS_DIR / "current_observations.jsonl"
    if not observed_path.exists():
        raise RuntimeError("No current observations available for RAGAS evaluation.")
    return [
        json.loads(line)
        for line in observed_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def main(argv: list[str] | None = None) -> int:
    load_dotenv(".env", override=False)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    parser.add_argument("--smoke-only", action="store_true")
    parser.add_argument("--case-id")
    parser.add_argument("--skip-ragas", action="store_true")
    parser.add_argument("--ragas-only", action="store_true")
    parser.add_argument("--keep-sessions", action="store_true")
    parser.add_argument(
        "--backend-url",
        default=os.getenv("SIMPLE_AGENT_EVAL_BACKEND_URL", "http://127.0.0.1:8000"),
    )
    parser.add_argument("--timeout-seconds", type=float, default=90)
    parser.add_argument(
        "--concurrency",
        type=int,
        default=1,
        help=(
            "Số ca chạy song song sau khi cổng khói đã qua. Mặc định 1 giữ nguyên "
            "hành vi tuần tự cũ. Cổng khói luôn chạy tuần tự."
        ),
    )
    args = parser.parse_args(argv)
    if args.ragas_only and (args.smoke_only or args.case_id or args.skip_ragas):
        parser.error("--ragas-only cannot be combined with --smoke-only, --case-id, or --skip-ragas.")

    ragas_config = RagasConfig.from_env()
    metadata: dict[str, Any] = {
        "run_id": f"simple-eval-{uuid.uuid4()}",
        "backend_url": args.backend_url,
        "git_sha": _git_sha(),
        "cases_path": str(args.cases),
        "ragas_version": ragas_version(),
        "ragas_llm_model": ragas_config.model,
        "ragas_embedding_model": ragas_config.embedding_model,
        "ragas_embedding_revision": ragas_config.embedding_revision,
    }
    evaluation_mode = "DETERMINISTIC_ONLY" if args.skip_ragas else "RAGAS"
    status = "COMPLETED"
    observations: list[dict[str, Any]] = []
    ragas_results: list[dict[str, Any]] = []
    ragas_errors: list[str] = []
    metrics: dict[str, Any] = {}
    session_ids: list[str] = []
    profile_ids: list[str] = []
    identity = client = None

    try:
        if args.ragas_only:
            observations = _current_observations()
            metrics = compute_metrics(observations)
            ragas_results, ragas_errors = run_ragas(observations, ragas_config)
            if ragas_errors:
                status = "EVALUATION_INCOMPLETE"
        else:
            cases = _load_cases(args.cases)
            metadata.update(_preflight(args.cases, cases))
            if args.case_id:
                execution = [case for case in cases if case.case_id == args.case_id]
                if not execution:
                    raise RuntimeError(f"Unknown case_id: {args.case_id}")
            else:
                smoke = [case for case in cases if case.smoke]
                remaining = [case for case in cases if not case.smoke]
                execution = smoke if args.smoke_only else smoke

            identity = ensure_eval_identity()
            client = SimpleAgentBackendClient(
                base_url=args.backend_url,
                token=identity.access_token,
                timeout_seconds=args.timeout_seconds,
            )
            client.healthcheck()
            observations = _run_cases(execution, client, identity, session_ids, profile_ids)
            if not args.case_id and _smoke_failed(observations):
                status = "SMOKE_FAILED"
            elif not args.smoke_only and not args.case_id:
                observations.extend(
                    _run_cases(
                        remaining,
                        client,
                        identity,
                        session_ids,
                        profile_ids,
                        concurrency=args.concurrency,
                    )
                )
            metrics = compute_metrics(observations)
            if not args.skip_ragas:
                ragas_results, ragas_errors = run_ragas(observations, ragas_config)
                if ragas_errors and status != "SMOKE_FAILED":
                    status = "EVALUATION_INCOMPLETE"
    except Exception as exc:
        status = "EVALUATION_INCOMPLETE"
        metadata["fatal_error"] = str(exc)
        metrics = compute_metrics(observations)
    finally:
        if client:
            client.close()
        if identity and not args.keep_sessions:
            try:
                metadata["cleaned_session_count"] = cleanup_run(
                    identity=identity, session_ids=session_ids, profile_ids=profile_ids
                )
            except Exception as exc:
                metadata["cleanup_error"] = str(exc)
        write_snapshot(
            observations=observations,
            ragas_results=ragas_results,
            metrics=metrics,
            metadata=metadata,
            status=status,
            ragas_errors=ragas_errors,
            evaluation_mode=evaluation_mode,
        )
    return 2 if status == "SMOKE_FAILED" else 3 if status == "EVALUATION_INCOMPLETE" else 0


if __name__ == "__main__":
    sys.exit(main())
