"""Compare base retrieval configurations on Dev only and freeze the winner."""

from __future__ import annotations

import hashlib
import json
import statistics
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.local_agent import pack_context
from src.retrieval import BM25Retriever, DensePgVectorRetriever, HybridRRFRetriever


def is_hit(chunk: dict, gold: list[dict]) -> bool:
    return any(
        chunk["source_id"] == item["source_id"]
        and chunk["page"] == item["page"]
        and item["evidence"] in chunk["text"]
        for item in gold
    )


def main() -> None:
    chunks = json.loads((ROOT / "data/day6/chunks.json").read_text(encoding="utf-8"))
    benchmark_path = ROOT / "benchmark/base_questions.json"
    benchmark = json.loads(benchmark_path.read_text(encoding="utf-8"))["questions"]
    dev = [row for row in benchmark if row["split"] == "dev" and row["answerable"]]
    assert len(dev) == 18

    dense = DensePgVectorRetriever()
    bm25 = BM25Retriever(chunks)
    configs = [
        ("dense_baseline", dense, 3, 3600, "Baseline exact cosine; same Day 6 embedding/index."),
        ("bm25", bm25, 3, 3600, "Lexical method; tests exact names and rare terms."),
        ("hybrid_rrf", HybridRRFRetriever(dense, bm25, candidate_k=10), 3, 3600,
         "Improvement 1: fuse complementary dense/lexical ranks without mixing raw scores."),
        ("hybrid_rrf_wide", HybridRRFRetriever(dense, bm25, candidate_k=15), 5, 5000,
         "Improvement 2: wider candidate/context budget may recover evidence missed at top 3."),
    ]
    output = ROOT / "artifacts/cp3/base_dev"
    output.mkdir(parents=True, exist_ok=True)
    summaries = []
    for config_id, retriever, top_k, budget, hypothesis in configs:
        traces = []
        for case in dev:
            started = time.perf_counter()
            results = retriever.search(case["question"], filters=case.get("filter"), top_k=top_k)
            elapsed_ms = (time.perf_counter() - started) * 1000
            marked = [{**row, "gold_hit": is_hit(row, case["gold"])} for row in results]
            context, context_ids = pack_context(marked, budget)
            traces.append({
                "query_id": case["id"], "split": "dev", "original_query": case["question"],
                "retrieval_query": case["question"], "query_transformed": False,
                "filter": case.get("filter"), "config_id": config_id, "top_k": top_k,
                "context_budget_chars": budget, "results": marked, "context": context,
                "context_ids": context_ids, "hit1": bool(marked and marked[0]["gold_hit"]),
                "hit3": any(row["gold_hit"] for row in marked[:3]),
                "context_hit": any(row["gold_hit"] and row["id"] in context_ids for row in marked),
                "elapsed_ms": round(elapsed_ms, 3), "service_cost_usd": 0,
            })
        summary = {
            "config_id": config_id, "split": "dev", "answerable_n": len(traces),
            "method": retriever.strategy, "top_k": top_k, "context_budget_chars": budget,
            "hypothesis": hypothesis,
            "hit1": sum(row["hit1"] for row in traces),
            "evidence_hit3": sum(row["hit3"] for row in traces),
            "context_evidence": sum(row["context_hit"] for row in traces),
            "median_retrieval_ms": round(statistics.median(row["elapsed_ms"] for row in traces), 3),
            "service_cost_usd": 0,
        }
        summaries.append(summary)
        (output / f"{config_id}_traces.json").write_text(
            json.dumps(traces, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )

    # Predeclared selection order: context evidence, Evidence Hit@3, Hit@1,
    # then lower median latency.  No Test information is available here.
    selected = max(summaries, key=lambda row: (
        row["context_evidence"], row["evidence_hit3"], row["hit1"], -row["median_retrieval_ms"]
    ))
    (output / "summary.json").write_text(
        json.dumps({"configs": summaries, "selected": selected["config_id"]}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    freeze = {
        "checkpoint": "CP3", "selection_split": "dev", "test_opened": False,
        "benchmark_sha256": hashlib.sha256(benchmark_path.read_bytes()).hexdigest(),
        "selection_rule": ["context_evidence", "evidence_hit3", "hit1", "lower_median_retrieval_ms"],
        "selected_config": selected,
        "selected_agent_config": {
            "retriever": selected["method"], "rewrite_query": False,
            "top_k": selected["top_k"], "context_budget_chars": selected["context_budget_chars"],
            "model": "Qwen/Qwen2.5-1.5B-Instruct",
            "reason": "Dev rewrite run introduced unsupported facts; original query preserved retrieval quality."
        },
        "test_run_count_at_freeze": 0,
    }
    (ROOT / "config/cp3_base_freeze.json").write_text(
        json.dumps(freeze, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({"configs": summaries, "selected": selected["config_id"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
