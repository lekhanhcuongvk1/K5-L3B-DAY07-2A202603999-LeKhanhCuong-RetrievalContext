"""Run reproducible CP2 Dev-only traces with a real local model and retrievers."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.local_agent import LocalQwen, run
from src.retrieval import BM25Retriever, DensePgVectorRetriever


def main() -> None:
    chunks = json.loads((ROOT / "data/day6/chunks.json").read_text(encoding="utf-8"))
    benchmark = json.loads((ROOT / "benchmark/base_questions.json").read_text(encoding="utf-8"))["questions"]
    by_id = {row["id"]: row for row in benchmark}
    cases = [by_id["B01"], by_id["B19"]]
    retrievers = [DensePgVectorRetriever(), BM25Retriever(chunks)]
    model = LocalQwen()
    traces = []
    for retriever in retrievers:
        for case in cases:
            trace = run(case["question"], model, retriever, filters=case.get("filter"))
            trace["query_id"] = case["id"]
            trace["split"] = "dev"
            trace["answerable"] = case["answerable"]
            traces.append(trace)
    output = ROOT / "artifacts/cp2"
    output.mkdir(parents=True, exist_ok=True)
    (output / "smoke_traces.json").write_text(
        json.dumps(traces, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    summary = {
        "checkpoint": "CP2", "split": "dev", "test_opened": False,
        "real_model": "Qwen/Qwen2.5-1.5B-Instruct", "mock_fallback": False,
        "retrieval_methods": [row.strategy for row in retrievers],
        "trace_count": len(traces), "service_cost_usd": 0,
        "statuses": {status: sum(t["status"] == status for t in traces) for status in ("answered", "abstain")},
    }
    (output / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
