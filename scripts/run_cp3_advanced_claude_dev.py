"""Run Claude on Advanced Dev with the selected retrieval contexts."""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.claude_agent import ClaudeProvider, answer_with_context
from src.local_agent import LocalQwen, pack_context
from src.retrieval import BM25Retriever, DensePgVectorRetriever, HybridRRFRetriever


def main() -> None:
    questions = json.loads((ROOT / "advanced/benchmark/questions.json").read_text(encoding="utf-8"))["questions"]
    dev = [row for row in questions if row["split"] == "dev"]
    positives = {row["query_id"]: row for row in json.loads(
        (ROOT / "artifacts/cp3/advanced_dev/advanced_hybrid_translated_wide_traces.json").read_text(encoding="utf-8")
    )}
    chunks = json.loads((ROOT / "advanced/derived/chunks.json").read_text(encoding="utf-8"))
    dense = DensePgVectorRetriever(table="day07_advanced_chunks")
    retriever = HybridRRFRetriever(dense, BM25Retriever(chunks), candidate_k=25)
    local, provider = LocalQwen(), ClaudeProvider()
    traces = []
    for index, case in enumerate(dev, 1):
        started = time.perf_counter()
        try:
            if case["id"] in positives:
                source = positives[case["id"]]
                query, results = source["retrieval_query"], source["results"]
                context, ids = source["context"], source["context_ids"]
            else:
                query = local.generate([
                    {"role": "system", "content": "Translate the full Vietnamese question into one English search query. Preserve names, numbers and conditions. Output English only."},
                    {"role": "user", "content": case["question"]},
                ], max_new_tokens=80).strip()
                results = retriever.search(query, filters=None, top_k=10)
                context, ids = pack_context(results, 14000)
            result = answer_with_context(case["question"], context, ids, provider)
            trace = {
                "status": result["status"], "question": case["question"], "answer": result["answer"],
                "citations": result["citations"], "events": [
                    {"event": "search", "tool": "hybrid_rrf", "query": query,
                     "query_transformed": True, "top_k": 10, "results": results,
                     "context": context, "context_ids": ids},
                    {"event": result["status"], "raw_model_output": result["raw_model_output"]},
                ], "usage": result["usage"],
                "timing_ms": {"answer_generation": result["answer_generation_ms"],
                              "total": round((time.perf_counter() - started) * 1000, 2)},
                "service_cost_usd": None,
                "cost_note": "Gateway reports tokens, not a USD price; no cost is fabricated.",
            }
        except Exception as error:
            trace = {"status": "error", "question": case["question"], "answer": "", "citations": [],
                     "events": ([{"event": "search", "tool": "hybrid_rrf", "query": query,
                                  "query_transformed": True, "top_k": 10, "results": results,
                                  "context": context, "context_ids": ids}]
                                if "context" in locals() else []),
                     "error": {"type": type(error).__name__, "message": str(error)},
                     "service_cost_usd": None}
        trace.update({"query_id": case["id"], "split": "dev", "answerable": case["answerable"],
                      "primary_group": case["primary_group"],
                      "config_id": "advanced_hybrid_translated_wide_claude",
                      "model": provider.model, "provider": "anthropic_compatible_gateway", "run_order": index})
        traces.append(trace)
        print(f"{index:02d}/{len(dev)} {case['id']} {trace['status']}", flush=True)
    output = ROOT / "artifacts/cp3/advanced_agent_dev"
    output.mkdir(parents=True, exist_ok=True)
    (output / "traces.json").write_text(json.dumps(traces, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"trace_count": len(traces), "answered": sum(t["status"] == "answered" for t in traces),
                      "abstained": sum(t["status"] == "abstain" for t in traces),
                      "errors": sum(t["status"] == "error" for t in traces)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
