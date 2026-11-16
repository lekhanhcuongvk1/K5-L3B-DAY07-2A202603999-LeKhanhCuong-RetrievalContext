"""Evaluate the improved Advanced pipeline on Dev only; resumable and auditable."""

from __future__ import annotations

import json
import os
import re
import sys
import time
import unicodedata
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.advanced_pipeline import (
    answer_with_coverage,
    build_query_plan,
    multi_query_search,
    pack_page_aware_context,
    prioritize_query_facets,
    question_requirements,
)
from src.claude_agent import ClaudeProvider
from src.local_agent import LocalQwen
from src.retrieval import BM25Retriever, DensePgVectorRetriever, HybridRRFRetriever


OUT_DIR = ROOT / "artifacts/improvement/advanced_dev_v2"
PLAN_OUT = OUT_DIR / "query_plans.json"
TRACE_OUT = OUT_DIR / "traces.json"


def normalize(value: str) -> str:
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKD", value).casefold()).strip()


def matches_gold(row: dict, gold: dict) -> bool:
    return row["page"] == gold["physical_pdf_page"] and any(
        normalize(term) in normalize(row["text"]) for term in gold["verification_terms"]
    )


def save(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    questions = json.loads(
        (ROOT / "advanced/benchmark/questions.json").read_text(encoding="utf-8")
    )["questions"]
    dev = [row for row in questions if row["split"] == "dev"]
    chunks = json.loads((ROOT / "advanced/derived/chunks.json").read_text(encoding="utf-8"))

    plans = json.loads(PLAN_OUT.read_text(encoding="utf-8")) if PLAN_OUT.exists() else {}
    for case in dev:
        if case["id"] in plans:
            plans[case["id"]]["requirements"] = question_requirements(case["question"])
    if plans:
        save(PLAN_OUT, plans)
    missing = [case for case in dev if case["id"] not in plans]
    if missing:
        local = LocalQwen()

        def translate(text: str) -> str:
            return local.generate([
                {
                    "role": "system",
                    "content": (
                        "Translate the Vietnamese text into a concise English document-search query. "
                        "Preserve every proper name, number, year, unit, comparison, and Figure/Table/Map "
                        "identifier. Do not answer. Output English only."
                    ),
                },
                {"role": "user", "content": text},
            ], max_new_tokens=120)

        for index, case in enumerate(missing, 1):
            plans[case["id"]] = build_query_plan(case["question"], translate)
            save(PLAN_OUT, plans)
            print(f"PLAN {index:02d}/{len(missing)} {case['id']}", flush=True)
        del local

    dense = DensePgVectorRetriever(table="day07_advanced_chunks")
    retriever = HybridRRFRetriever(dense, BM25Retriever(chunks), candidate_k=30)
    provider = ClaudeProvider()
    traces = json.loads(TRACE_OUT.read_text(encoding="utf-8")) if TRACE_OUT.exists() else []
    rerun_ids = {
        value.strip() for value in os.getenv("IMPROVEMENT_RERUN_IDS", "").split(",")
        if value.strip()
    }
    completed = {
        row["query_id"] for row in traces
        if row["status"] != "error" and row["query_id"] not in rerun_ids
    }

    for case in dev:
        if case["id"] in completed:
            print(f"SKIP {case['id']}", flush=True)
            continue
        started = time.perf_counter()
        plan = plans[case["id"]]
        try:
            search_started = time.perf_counter()
            ranked, result_sets = multi_query_search(
                retriever, plan["queries"], per_query_k=15, top_k=24
            )
            search_ms = (time.perf_counter() - search_started) * 1000
            context_ranked = prioritize_query_facets(ranked, result_sets, depth=5)
            context, context_ids, context_pages = pack_page_aware_context(
                context_ranked, chunks, budget_chars=18000, seed_pages=6
            )
            result = answer_with_coverage(
                case["question"], plan["requirements"], context, context_ids, provider
            )
            marked = []
            for row in ranked:
                regions = [
                    index for index, gold in enumerate(case.get("gold", []))
                    if matches_gold(row, gold)
                ]
                marked.append({**row, "matched_gold_regions": regions, "gold_hit": bool(regions)})
            found = {
                index for row in marked if row["id"] in context_ids
                for index in row["matched_gold_regions"]
            }
            trace = {
                "query_id": case["id"], "split": "dev", "answerable": case["answerable"],
                "primary_group": case["primary_group"], "status": result["status"],
                "question": case["question"], "answer": result["answer"],
                "citations": result["citations"], "coverage": result.get("coverage", []),
                "events": [{
                    "event": "multi_query_search", "tool": "multi_query_hybrid_rrf",
                    "query_plan": plan, "per_query_top_k": 15,
                    "result_set_sizes": [len(rows) for rows in result_sets],
                    "results": marked, "context": context, "context_ids": context_ids,
                    "context_pages": context_pages,
                    "context_selection": "six_seed_pages_with_previous_same_next_page_expansion",
                }, {"event": result["status"], "raw_model_output": result["raw_model_output"],
                    "format_repair_used": result.get("format_repair_used", False),
                    "original_raw_model_output": result.get("original_raw_model_output")}],
                "retrieval_metrics": ({
                    "hit1": bool(marked and marked[0]["gold_hit"]),
                    "evidence_hit3": any(row["gold_hit"] for row in marked[:3]),
                    "complete_context_evidence": len(found) == len(case["gold"]),
                    "found_gold_regions": sorted(found),
                } if case["answerable"] else None),
                "usage": result["usage"],
                "timing_ms": {
                    "retrieval": round(search_ms, 2),
                    "answer_generation": result["answer_generation_ms"],
                    "total": round((time.perf_counter() - started) * 1000, 2),
                },
                "model": provider.model, "provider": "anthropic_compatible_gateway",
                "service_cost_usd": None,
                "cost_note": "Gateway returned tokens but no USD price; no cost was fabricated.",
            }
        except Exception as error:
            trace = {
                "query_id": case["id"], "split": "dev", "answerable": case["answerable"],
                "primary_group": case["primary_group"], "status": "error",
                "question": case["question"], "answer": "", "citations": [], "events": [],
                "error": {"type": type(error).__name__, "message": str(error)},
                "model": provider.model, "provider": "anthropic_compatible_gateway",
                "service_cost_usd": None,
            }
        traces = [row for row in traces if row["query_id"] != case["id"]] + [trace]
        save(TRACE_OUT, traces)
        if trace["status"] != "error":
            completed.add(case["id"])
        print(f"{len(completed):02d}/{len(dev)} {case['id']} {trace['status']}", flush=True)

    print(json.dumps({
        "traces": len(traces),
        "errors": sum(row["status"] == "error" for row in traces),
    }))


if __name__ == "__main__":
    main()
