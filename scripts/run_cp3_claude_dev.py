"""Run frozen candidate retrieval with Claude-compatible provider on Base Dev."""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.claude_agent import ClaudeProvider, answer_with_context
from src.local_agent import pack_context
from src.retrieval import BM25Retriever


def main() -> None:
    chunks = json.loads((ROOT / "data/day6/chunks.json").read_text(encoding="utf-8"))
    questions = json.loads((ROOT / "benchmark/base_questions.json").read_text(encoding="utf-8"))["questions"]
    dev = [row for row in questions if row["split"] == "dev"]
    retriever, provider = BM25Retriever(chunks), ClaudeProvider()
    traces = []
    for index, case in enumerate(dev, 1):
        started = time.perf_counter()
        try:
            search_started = time.perf_counter()
            results = retriever.search(case["question"], filters=case.get("filter"), top_k=3)
            search_ms = (time.perf_counter() - search_started) * 1000
            context, ids = pack_context(results, 3600)
            result = answer_with_context(case["question"], context, ids, provider)
            trace = {
                "status": result["status"], "question": case["question"], "answer": result["answer"],
                "citations": result["citations"], "events": [
                    {"event": "search", "tool": "bm25", "query": case["question"],
                     "query_transformed": False, "filter": case.get("filter"), "top_k": 3,
                     "results": results, "context": context, "context_ids": ids},
                    {"event": result["status"], "raw_model_output": result["raw_model_output"]},
                ], "usage": result["usage"],
                "timing_ms": {"retrieval": round(search_ms, 2),
                              "answer_generation": result["answer_generation_ms"],
                              "total": round((time.perf_counter() - started) * 1000, 2)},
                "service_cost_usd": None,
                "cost_note": "Gateway response exposes tokens but not a USD price; no cost is fabricated.",
            }
        except Exception as error:
            trace = {"status": "error", "question": case["question"], "answer": "", "citations": [],
                     "events": [], "error": {"type": type(error).__name__, "message": str(error)},
                     "service_cost_usd": None}
        trace.update({"query_id": case["id"], "split": "dev", "answerable": case["answerable"],
                      "config_id": "bm25_original_query_claude", "run_order": index,
                      "model": provider.model, "provider": "anthropic_compatible_gateway"})
        traces.append(trace)
        print(f"{index:02d}/{len(dev)} {case['id']} {trace['status']}", flush=True)
    output = ROOT / "artifacts/cp3/base_agent_claude_dev"
    output.mkdir(parents=True, exist_ok=True)
    (output / "traces.json").write_text(json.dumps(traces, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"trace_count": len(traces), "answered": sum(t["status"] == "answered" for t in traces),
                      "abstained": sum(t["status"] == "abstain" for t in traces),
                      "errors": sum(t["status"] == "error" for t in traces)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
