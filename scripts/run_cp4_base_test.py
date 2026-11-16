"""Run Base Test once for dense baseline and the frozen BM25 configuration.

The runner checkpoints after every query and resumes without repeating completed
provider calls. Gold is used only after retrieval for offline metrics; it never
enters the query, context, or model prompt.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.claude_agent import ClaudeProvider, answer_with_context
from src.local_agent import pack_context
from src.retrieval import BM25Retriever, DensePgVectorRetriever


OUT = ROOT / "artifacts/cp4/base_test/traces.json"


def hit(row: dict, gold: list[dict]) -> bool:
    return any(row["source_id"] == item["source_id"] and row["page"] == item["page"]
               and item["evidence"] in row["text"] for item in gold)


def save(rows: list[dict]) -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    freeze = json.loads((ROOT / "config/cp3_base_freeze.json").read_text(encoding="utf-8"))
    if freeze["test_run_count_at_freeze"] != 0:
        raise SystemExit("Invalid freeze: Test had already been run")
    chunks = json.loads((ROOT / "data/day6/chunks.json").read_text(encoding="utf-8"))
    questions = json.loads((ROOT / "benchmark/base_questions.json").read_text(encoding="utf-8"))["questions"]
    test = [row for row in questions if row["split"] == "test"]
    if len(test) != 9:
        raise SystemExit("Expected exactly 9 Base Test questions")
    dense = DensePgVectorRetriever()
    configs = [("dense_baseline", dense), ("bm25_selected", BM25Retriever(chunks))]
    provider = ClaudeProvider()
    traces = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else []
    completed = {(row["config_id"], row["query_id"]) for row in traces if row["status"] != "error"}
    for config_id, retriever in configs:
        for case in test:
            key = (config_id, case["id"])
            if key in completed:
                print(f"SKIP {config_id} {case['id']}", flush=True)
                continue
            started = time.perf_counter()
            try:
                search_started = time.perf_counter()
                results = retriever.search(case["question"], filters=case.get("filter"), top_k=3)
                search_ms = (time.perf_counter() - search_started) * 1000
                marked = [{**row, "gold_hit": hit(row, case.get("gold", []))} for row in results]
                context, ids = pack_context(marked, 3600)
                result = answer_with_context(case["question"], context, ids, provider)
                trace = {
                    "query_id": case["id"], "split": "test", "answerable": case["answerable"],
                    "config_id": config_id, "status": result["status"], "question": case["question"],
                    "answer": result["answer"], "citations": result["citations"],
                    "events": [{"event": "search", "tool": retriever.strategy,
                                "query": case["question"], "query_transformed": False,
                                "filter": case.get("filter"), "top_k": 3, "results": marked,
                                "context": context, "context_ids": ids},
                               {"event": result["status"], "raw_model_output": result["raw_model_output"]}],
                    "retrieval_metrics": ({"hit1": bool(marked and marked[0]["gold_hit"]),
                                           "evidence_hit3": any(row["gold_hit"] for row in marked),
                                           "context_evidence": any(row["gold_hit"] and row["id"] in ids for row in marked)}
                                          if case["answerable"] else None),
                    "usage": result["usage"],
                    "timing_ms": {"retrieval": round(search_ms, 2),
                                  "answer_generation": result["answer_generation_ms"],
                                  "total": round((time.perf_counter() - started) * 1000, 2)},
                    "model": provider.model, "provider": "anthropic_compatible_gateway",
                    "service_cost_usd": None,
                    "cost_note": "Gateway returned tokens but no USD price; no cost was fabricated.",
                }
            except Exception as error:
                trace = {"query_id": case["id"], "split": "test", "answerable": case["answerable"],
                         "config_id": config_id, "status": "error", "question": case["question"],
                         "answer": "", "citations": [], "events": [],
                         "error": {"type": type(error).__name__, "message": str(error)},
                         "model": provider.model, "provider": "anthropic_compatible_gateway",
                         "service_cost_usd": None}
            traces = [row for row in traces if (row["config_id"], row["query_id"]) != key] + [trace]
            save(traces)
            print(f"{len(completed)+1:02d}/18 {config_id} {case['id']} {trace['status']}", flush=True)
            if trace["status"] != "error":
                completed.add(key)
    print(json.dumps({"traces": len(traces), "errors": sum(row["status"] == "error" for row in traces)}))


if __name__ == "__main__":
    main()
