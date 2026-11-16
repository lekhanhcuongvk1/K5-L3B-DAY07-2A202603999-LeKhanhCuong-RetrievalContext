"""Quality gate for CP2 real-model, real-retrieval traces."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load(path: str):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def main() -> None:
    model = load("artifacts/model_validation.json")
    assert model["agent_model"] == "Qwen/Qwen2.5-1.5B-Instruct"
    assert model["agent_revision"] == "989aa7980e4cf806f80c7fef2b1adb7bc71aa306"
    assert model["agent_snapshot_present"] is True

    summary = load("artifacts/cp2/summary.json")
    traces = load("artifacts/cp2/smoke_traces.json")
    reviews = load("artifacts/cp2/reviews.json")
    assert summary["split"] == "dev" and summary["test_opened"] is False
    assert summary["mock_fallback"] is False
    assert set(summary["retrieval_methods"]) == {"dense_pgvector", "bm25"}
    assert len(traces) == len(reviews) == 4
    assert all(trace["model"]["provider"] == "local_huggingface" for trace in traces)
    assert all(trace["events"][0]["event"] == "search" for trace in traces)
    assert all(trace["events"][0]["results"] for trace in traces)
    assert all(trace["events"][0]["context"] for trace in traces)
    assert all(trace["service_cost_usd"] == 0 for trace in traces)

    by_case = {(trace["query_id"], trace["events"][0]["tool"]): trace for trace in traces}
    for strategy in ("dense_pgvector", "bm25"):
        positive = by_case[("B01", strategy)]
        negative = by_case[("B19", strategy)]
        assert positive["status"] == "answered" and len(positive["citations"]) == 1
        assert positive["citations"][0] in positive["events"][0]["context_ids"]
        cited = next(row for row in positive["events"][0]["results"] if row["id"] == positive["citations"][0])
        assert "BASIC là viết tắt" in cited["text"] and "S ymbolic" in cited["text"]
        assert negative["status"] == "abstain" and not negative["citations"]

    assert all(review.get("answer_grade") == 2 for review in reviews if review["query_id"] == "B01")
    assert all(review.get("abstention_correct") is True for review in reviews if review["query_id"] == "B19")
    print("CP2 quality gate: PASS")


if __name__ == "__main__":
    main()
