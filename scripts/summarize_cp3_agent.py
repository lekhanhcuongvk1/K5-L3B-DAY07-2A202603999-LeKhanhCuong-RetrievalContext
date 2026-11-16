"""Aggregate the manually reviewed CP3 Dev agent run."""

from __future__ import annotations

import json
import statistics
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DIR = ROOT / "artifacts/cp3/base_agent_dev"


def main() -> None:
    traces = json.loads((DIR / "traces.json").read_text(encoding="utf-8"))
    reviews = json.loads((DIR / "reviews.json").read_text(encoding="utf-8"))
    review_by_id = {row["query_id"]: row for row in reviews}
    answerable = [row for row in traces if row["answerable"]]
    negative = [row for row in traces if not row["answerable"]]
    citation_flags = [flag for review in reviews for flag in review["citation_support"]]
    grades = [review_by_id[row["query_id"]]["answer_grade"] for row in answerable]
    timings = [row["timing_ms"]["total"] for row in traces if "timing_ms" in row]
    summary = {
        "split": "dev", "config_id": "bm25_original_query",
        "trace_count": len(traces), "successful_runs": sum(row["status"] != "error" for row in traces),
        "errors": sum(row["status"] == "error" for row in traces),
        "tool_use": sum(any(event.get("event") == "search" for event in row["events"]) for row in traces),
        "search_calls_distribution": {"1": sum(sum(e.get("event") == "search" for e in row["events"]) == 1 for row in traces)},
        "grounded_answer_grades": {str(value): grades.count(value) for value in (0, 1, 2)},
        "grounded_answer_mean_over_2": round(statistics.mean(grades), 3),
        "citation_validity": {"valid": sum(citation_flags), "total": len(citation_flags),
                              "rate": round(sum(citation_flags) / len(citation_flags), 3)},
        "answers_with_citation": sum(bool(row["citations"]) for row in traces),
        "abstention": {"correct": sum(review_by_id[row["query_id"]]["abstention_correct"] for row in negative),
                       "total_unanswerable": len(negative),
                       "false_refusals": sum(row["status"] == "abstain" for row in answerable),
                       "answerable_total": len(answerable)},
        "median_total_ms": round(statistics.median(timings), 2),
        "service_cost_usd": 0, "test_opened": False, "human_reviewed": True,
    }
    (DIR / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
