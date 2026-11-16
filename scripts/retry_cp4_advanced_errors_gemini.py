"""Retry only Advanced Test provider errors using the configured Gemini fallback."""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.claude_agent import answer_with_context
from src.gemini_agent import GeminiProvider
from src.retrieval import BM25Retriever, DensePgVectorRetriever, HybridRRFRetriever
from scripts.run_cp4_advanced_test import pack_rank_interleaved


def main() -> None:
    trace_path = ROOT / "artifacts/cp4/advanced_test/traces.json"
    traces = json.loads(trace_path.read_text(encoding="utf-8"))
    errors = [trace for trace in traces if trace["status"] == "error"]
    if not errors:
        print(json.dumps({"retried": 0, "remaining_errors": 0}))
        return
    questions = {row["id"]: row for row in json.loads(
        (ROOT / "advanced/benchmark/questions.json").read_text(encoding="utf-8")
    )["questions"]}
    translations = json.loads((ROOT / "artifacts/cp4/advanced_test/query_translations.json").read_text(encoding="utf-8"))
    chunks = json.loads((ROOT / "advanced/derived/chunks.json").read_text(encoding="utf-8"))
    dense = DensePgVectorRetriever(table="day07_advanced_chunks")
    retriever = HybridRRFRetriever(dense, BM25Retriever(chunks), candidate_k=25)
    provider = GeminiProvider()
    for trace in errors:
        case = questions[trace["query_id"]]
        query = translations[trace["query_id"]]["translated_query"]
        started = time.perf_counter()
        results = retriever.search(query, filters=None, top_k=10)
        context, ids = pack_rank_interleaved(results, chunks)
        result = answer_with_context(case["question"], context, ids, provider)
        trace.update({
            "status": result["status"], "answer": result["answer"],
            "citations": result["citations"], "usage": result["usage"],
            "events": [
                {"event": "search", "tool": "hybrid_rrf", "query": query,
                 "query_transformed": True, "top_k": 10, "results": results,
                 "context": context, "context_ids": ids,
                 "context_selection": "rank_interleaved_same_page_then_adjacent_page"},
                {"event": result["status"], "raw_model_output": result["raw_model_output"]},
            ],
            "timing_ms": {"answer_generation": result["answer_generation_ms"],
                          "total": round((time.perf_counter() - started) * 1000, 2)},
            "model": provider.model, "provider": "google_gemini_official",
            "fallback_reason": "Primary Anthropic-compatible gateway repeatedly failed this query.",
            "fallback_attempts": trace.get("fallback_attempts", 0) + 1,
            "service_cost_usd": None,
            "cost_note": "Provider response did not include a USD charge; no cost was fabricated.",
        })
        trace.pop("error", None)
        trace_path.write_text(json.dumps(traces, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"{trace['query_id']} {trace['status']} via {provider.model}", flush=True)
    print(json.dumps({"retried": len(errors),
                      "remaining_errors": sum(trace["status"] == "error" for trace in traces)}))


if __name__ == "__main__":
    main()
