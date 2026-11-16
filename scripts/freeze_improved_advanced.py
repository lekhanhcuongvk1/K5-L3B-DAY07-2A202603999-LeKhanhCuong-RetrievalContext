"""Validate reviewed Dev artifacts and freeze the improved pipeline before new Test."""

from __future__ import annotations

import hashlib
import json
import statistics
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "artifacts/improvement/advanced_dev_v2"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    traces = load(ARTIFACT / "traces.json")
    reviews = load(ARTIFACT / "reviews.json")
    assert len(traces) == 20 and len(reviews) == 20
    assert {row["query_id"] for row in traces} == {f"A{number:02d}" for number in range(1, 21)}
    assert all(row["split"] == "dev" and row["status"] != "error" for row in traces)
    assert all(row["pass"] for row in reviews)
    assert sum(row["status"] == "abstain" for row in traces) == 3

    summary = {
        "split": "dev",
        "n": 20,
        "passed": 20,
        "pass_rate": 1.0,
        "answered": 17,
        "abstained": 3,
        "errors": 0,
        "complete_context_evidence_by_original_locator": sum(
            bool(row.get("retrieval_metrics", {}).get("complete_context_evidence"))
            for row in traces if row["answerable"]
        ),
        "answerable_n": 17,
        "input_tokens": sum(row.get("usage", {}).get("input_tokens", 0) for row in traces),
        "output_tokens": sum(row.get("usage", {}).get("output_tokens", 0) for row in traces),
        "median_total_ms": round(statistics.median(row["timing_ms"]["total"] for row in traces), 2),
        "service_cost_usd": None,
        "cost_note": "Gateway returned token usage but no USD price; no cost was fabricated.",
        "human_reviewed": True,
    }
    (ARTIFACT / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    tracked = [
        ROOT / "src/advanced_pipeline.py",
        ROOT / "scripts/run_improved_advanced_dev.py",
        ROOT / "artifacts/improvement/advanced_dev_v2/query_plans.json",
        ROOT / "artifacts/improvement/advanced_dev_v2/traces.json",
        ROOT / "artifacts/improvement/advanced_dev_v2/reviews.json",
    ]
    freeze = {
        "freeze_id": "advanced-pipeline-v2-before-independent-test",
        "selection_split": "dev",
        "selected_config": {
            "retrieval": "multi-query hybrid RRF",
            "per_query_top_k": 15,
            "fused_top_k": 24,
            "facet_priority_depth": 5,
            "context_budget_chars": 18000,
            "context_selection": "facet-round-robin candidates then previous/same/next page expansion",
            "answer_validation": "requirement coverage with one format-only repair on malformed JSON",
        },
        "dev_result": {"passed": 20, "n": 20},
        "independent_test_created_at_freeze": False,
        "independent_test_run_count_at_freeze": 0,
        "files_sha256": {str(path.relative_to(ROOT)).replace("\\", "/"): sha256(path) for path in tracked},
    }
    output = ROOT / "config/improved_advanced_freeze.json"
    output.write_text(json.dumps(freeze, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"freeze": "PASS", "dev": "20/20", "output": str(output.relative_to(ROOT))}))


if __name__ == "__main__":
    main()
