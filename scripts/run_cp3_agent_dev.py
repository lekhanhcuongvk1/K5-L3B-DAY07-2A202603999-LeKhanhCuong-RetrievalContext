"""Run the selected base configuration with the real local agent on all Dev cases."""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.local_agent import LocalQwen, run
from src.retrieval import BM25Retriever


def main() -> None:
    chunks = json.loads((ROOT / "data/day6/chunks.json").read_text(encoding="utf-8"))
    questions = json.loads((ROOT / "benchmark/base_questions.json").read_text(encoding="utf-8"))["questions"]
    dev = [row for row in questions if row["split"] == "dev"]
    assert len(dev) == 21
    model = LocalQwen()
    retriever = BM25Retriever(chunks)
    traces = []
    for index, case in enumerate(dev, 1):
        try:
            trace = run(case["question"], model, retriever, filters=case.get("filter"), top_k=3,
                        budget_chars=3600, rewrite_query=False)
        except Exception as error:
            trace = {
                "status": "error", "question": case["question"], "answer": "", "citations": [],
                "events": [], "error": {"type": type(error).__name__, "message": str(error)},
                "service_cost_usd": 0,
            }
        trace.update({"query_id": case["id"], "split": "dev", "answerable": case["answerable"],
                      "config_id": "bm25_original_query", "run_order": index})
        traces.append(trace)
        print(f"{index:02d}/{len(dev)} {case['id']} {trace['status']}", flush=True)
    output = ROOT / "artifacts/cp3/base_agent_dev"
    output.mkdir(parents=True, exist_ok=True)
    (output / "traces.json").write_text(json.dumps(traces, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    summary = {
        "split": "dev", "config_id": "bm25_original_query", "model": "Qwen/Qwen2.5-1.5B-Instruct",
        "trace_count": len(traces), "answered": sum(t["status"] == "answered" for t in traces),
        "abstained": sum(t["status"] == "abstain" for t in traces),
        "errors": sum(t["status"] == "error" for t in traces),
        "tool_use": sum(any(e.get("event") == "search" for e in t["events"]) for t in traces),
        "service_cost_usd": 0, "test_opened": False,
    }
    (output / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
