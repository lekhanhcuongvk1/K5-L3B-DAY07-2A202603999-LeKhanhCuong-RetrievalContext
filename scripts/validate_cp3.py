"""CP3 quality gate: methods, Dev-only traces, reviews and frozen configs."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load(path: str):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def main() -> None:
    base = load("artifacts/cp3/base_dev/summary.json")
    configs = {row["config_id"]: row for row in base["configs"]}
    assert {row["method"] for row in configs.values()} >= {"dense_pgvector", "bm25", "hybrid_rrf"}
    assert configs["dense_baseline"]["evidence_hit3"] == 14
    assert configs["bm25"]["evidence_hit3"] == 17
    assert len([row for row in configs.values() if row["config_id"] != "dense_baseline"]) >= 2

    advanced_index = load("artifacts/cp3/advanced_index.json")
    assert advanced_index["physical_pages"] == 409
    assert advanced_index["indexed_pages"] == 397
    assert advanced_index["database_rows"] == advanced_index["chunk_count"] == 1076
    assert len(advanced_index["skipped_pages"]) == 12
    assert all(advanced_index["modality_counts"][key] > 0 for key in ("text", "table", "chart", "image_or_diagram"))

    base_freeze = load("config/cp3_base_freeze.json")
    advanced_freeze = load("config/cp3_advanced_freeze.json")
    assert base_freeze["test_opened"] is False and base_freeze["test_run_count_at_freeze"] == 0
    assert advanced_freeze["test_opened"] is False and advanced_freeze["test_run_count_at_freeze"] == 0
    assert base_freeze["benchmark_sha256"] == hashlib.sha256((ROOT / "benchmark/base_questions.json").read_bytes()).hexdigest()
    assert advanced_freeze["benchmark_sha256"] == hashlib.sha256((ROOT / "advanced/benchmark/questions.json").read_bytes()).hexdigest()

    for prefix, expected_n, expected_pass in (
        ("base_agent_claude_dev", 21, 20), ("advanced_agent_dev", 20, 19)
    ):
        summary = load(f"artifacts/cp3/{prefix}/summary.json")
        traces = load(f"artifacts/cp3/{prefix}/traces.json")
        reviews = load(f"artifacts/cp3/{prefix}/reviews.json")
        assert summary["n"] == len(traces) == len(reviews) == expected_n
        assert summary["passed"] == expected_pass and summary["errors"] == 0
        assert summary["test_opened"] is False and summary["human_reviewed"] is True
        assert all(trace["split"] == "dev" for trace in traces)
        assert all(trace.get("service_cost_usd") is None for trace in traces)
        assert all(trace.get("provider") == "anthropic_compatible_gateway" for trace in traces)

    ignored = subprocess.run(["git", "check-ignore", ".env"], cwd=ROOT, capture_output=True, text=True, check=True)
    assert ".env" in ignored.stdout
    tracked = subprocess.run(["git", "ls-files", ".env"], cwd=ROOT, capture_output=True, text=True, check=True)
    assert not tracked.stdout.strip()
    print("CP3 quality gate: PASS")


if __name__ == "__main__":
    main()
