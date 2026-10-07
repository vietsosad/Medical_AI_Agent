"""Current-snapshot artifacts and human-readable RAGAS evaluation report."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


RESULTS_DIR = Path("eval/results")
RAGAS_SCORE_FIELDS = (
    "faithfulness_score",
    "context_precision_score",
    "context_recall_score",
    "context_relevance_score",
    "answer_relevancy_score",
)


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, ensure_ascii=False, default=str) + "\n" for row in rows), encoding="utf-8")


def _ragas_breakdown(ragas_results: list[dict[str, Any]]) -> dict[str, float]:
    completed = [
        row for row in ragas_results
        if row.get("ragas_applicable") and row.get("verdict") not in {"incomplete", "skipped"}
    ]
    if not completed:
        return {}
    return {
        field: round(
            sum(float(row[field]) for row in completed if row.get(field) is not None)
            / len(completed),
            4,
        )
        for field in RAGAS_SCORE_FIELDS
    }


def verdict(
    metrics: dict[str, Any],
    ragas_results: list[dict[str, Any]],
    status: str,
    evaluation_mode: str,
) -> tuple[str, float | None]:
    if status == "SMOKE_FAILED":
        return status, 0.0
    if status != "COMPLETED":
        return "EVALUATION_INCOMPLETE", None

    deterministic_score = float(metrics.get("deterministic_score", 0))
    applicable = [row for row in ragas_results if row.get("ragas_applicable")]
    incomplete = [row for row in applicable if row.get("verdict") == "incomplete"]
    if evaluation_mode == "DETERMINISTIC_ONLY":
        overall = round(deterministic_score, 4)
    elif incomplete or not applicable:
        return "EVALUATION_INCOMPLETE", None
    else:
        ragas_score = sum(float(row["ragas_score"]) for row in applicable) / len(applicable)
        overall = round(0.8 * deterministic_score + 0.2 * ragas_score, 4)

    if metrics.get("hard_fail_reasons"):
        return "FAIL", overall
    if overall >= 0.80:
        return "PASS", overall
    if overall >= 0.65:
        return "WARNING", overall
    return "FAIL", overall


def write_snapshot(
    *,
    observations: list[dict[str, Any]],
    ragas_results: list[dict[str, Any]],
    metrics: dict[str, Any],
    metadata: dict[str, Any],
    status: str,
    ragas_errors: list[str],
    evaluation_mode: str,
) -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    final_verdict, overall = verdict(metrics, ragas_results, status, evaluation_mode)
    ragas_breakdown = _ragas_breakdown(ragas_results)
    applicable_count = sum(row.get("ragas_applicable") for row in ragas_results)
    incomplete_count = sum(
        row.get("ragas_applicable") and row.get("verdict") == "incomplete"
        for row in ragas_results
    )
    skipped_count = sum((not row.get("ragas_applicable")) or row.get("verdict") == "skipped" for row in ragas_results)
    metrics = {
        **metrics,
        "overall_score": overall,
        "verdict": final_verdict,
        "evaluation_mode": evaluation_mode,
        "ragas_result_count": len(ragas_results),
        "ragas_applicable_count": applicable_count,
        "ragas_skipped_count": skipped_count,
        "ragas_incomplete_count": incomplete_count,
        "ragas_scores": ragas_breakdown,
        "ragas_errors": ragas_errors,
    }
    metadata = {**metadata, "status": status, "written_at": datetime.now(UTC).isoformat()}
    _write_jsonl(RESULTS_DIR / "current_observations.jsonl", observations)
    _write_jsonl(RESULTS_DIR / "current_ragas_results.jsonl", ragas_results)
    _write_json(RESULTS_DIR / "current_metrics.json", metrics)
    _write_json(RESULTS_DIR / "current_run_metadata.json", metadata)

    classification = metrics.get("classification", {})
    retrieval = metrics.get("retrieval_protocol", {})
    failures = [
        row for row in observations
        if row.get("expected_esi") is not None and row.get("predicted_esi") != row.get("expected_esi")
    ]
    overall_text = f"{overall:.2%}" if overall is not None else "not available"
    lines = [
        "# Simple Agent RAGAS Evaluation Snapshot", "",
        f"- Status: **{status}**",
        f"- Verdict: **{final_verdict}**",
        f"- Evaluation mode: `{evaluation_mode}`",
        f"- Overall score: **{overall_text}**",
        f"- Backend: `{metadata.get('backend_url', 'unknown')}`",
        f"- Run time (UTC): {metadata['written_at']}", "",
        "## Deterministic classification", "",
        f"- Accuracy: {classification.get('accuracy', 0):.2%}",
        f"- Macro F1: {classification.get('macro_f1', 0):.2%}",
        f"- Missing prediction: {classification.get('missing_prediction_count', 0)}",
        f"- Critical ESI 1/2 undertriage: {classification.get('critical_undertriage_count', 0)}", "",
        "## Deterministic retrieval & evidence", "",
        f"- Recall@5: {retrieval.get('recall_at_5', 0):.2%}",
        f"- Precision@5: {retrieval.get('precision_at_5', 0):.2%}",
        f"- MRR: {retrieval.get('mrr', 0):.2%}",
        f"- nDCG@5: {retrieval.get('ndcg_at_5', 0):.2%}",
        f"- Citation support: {retrieval.get('citation_support_rate', 0):.2%}", "",
        "## RAGAS quality", "",
        f"- Applicable: {applicable_count}; skipped: {skipped_count}; incomplete: {incomplete_count}",
    ]
    if ragas_breakdown:
        labels = {
            "faithfulness_score": "Faithfulness",
            "context_precision_score": "Context precision",
            "context_recall_score": "Context recall",
            "context_relevance_score": "Context relevance",
            "answer_relevancy_score": "Answer relevancy",
        }
        lines.extend(f"- {labels[field]}: {value:.2%}" for field, value in ragas_breakdown.items())
    else:
        lines.append("- No completed RAGAS result.")

    lines += ["", "## Classification mismatches", ""]
    if not failures:
        lines.append("No deterministic classification mismatch.")
    else:
        lines += ["| Case | Expected | Predicted | Terminal action |", "| --- | ---: | ---: | --- |"]
        lines += [
            f"| {item['case_id']} | {item.get('expected_esi')} | {item.get('predicted_esi') or 'missing'} | {item.get('terminal_action')} |"
            for item in failures
        ]

    ragas_alerts = [
        row for row in ragas_results
        if row.get("ragas_applicable") and row.get("verdict") in {"warning", "fail", "incomplete"}
    ]
    lines += ["", "## RAGAS warning, fail, or incomplete cases", ""]
    if not ragas_alerts:
        lines.append("No RAGAS warning, fail, or incomplete case.")
    else:
        lines += ["| Case | Verdict | RAGAS score | Errors |", "| --- | --- | ---: | --- |"]
        for row in ragas_alerts:
            score = row.get("ragas_score")
            score_text = f"{score:.2%}" if score is not None else "n/a"
            errors = "; ".join(row.get("metric_errors", {}).keys()) or "-"
            lines.append(f"| {row['case_id']} | {row['verdict']} | {score_text} | {errors} |")
    if metrics.get("hard_fail_reasons"):
        lines += ["", "## Hard-fail reasons", "", *[f"- {reason}" for reason in metrics["hard_fail_reasons"]]]
    if ragas_errors:
        lines += ["", "## RAGAS availability", "", *[f"- {error}" for error in ragas_errors]]
    lines += ["", "This report evaluates Simple Agent output and evidence only. It does not use DeepAgent sessions or real user chat history."]
    (RESULTS_DIR / "current_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
