"""Run the frozen v2 pipeline on the sealed independent Test, resumably."""

from __future__ import annotations

import hashlib, json, re, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.run_improved_advanced_dev import matches_gold, save
from src.advanced_pipeline import (answer_with_coverage, build_query_plan, multi_query_search,
    pack_page_aware_context, prioritize_query_facets)
from src.claude_agent import ClaudeProvider
from src.local_agent import LocalQwen
from src.retrieval import BM25Retriever, DensePgVectorRetriever, HybridRRFRetriever

BENCH = ROOT / "advanced/benchmark_v2/questions.json"
FREEZE = ROOT / "advanced/benchmark_v2/freeze.json"
OUT = ROOT / "artifacts/improvement/independent_test_v2"


def main() -> None:
    freeze = json.loads(FREEZE.read_text(encoding="utf-8"))
    assert freeze["test_run_count"] == 0
    assert hashlib.sha256(BENCH.read_bytes()).hexdigest() == freeze["questions_sha256"]
    pipeline_freeze = json.loads((ROOT / "config/improved_advanced_freeze.json").read_text(encoding="utf-8"))
    for relative, expected in pipeline_freeze["files_sha256"].items():
        assert hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() == expected, f"frozen file changed: {relative}"

    cases = json.loads(BENCH.read_text(encoding="utf-8"))["questions"]
    chunks = json.loads((ROOT / "advanced/derived/chunks.json").read_text(encoding="utf-8"))
    plan_path, trace_path = OUT / "query_plans.json", OUT / "traces.json"
    plans = json.loads(plan_path.read_text(encoding="utf-8")) if plan_path.exists() else {}
    missing = [case for case in cases if case["id"] not in plans]
    if missing:
        local = LocalQwen()
        def translate(text):
            return local.generate([
                {"role":"system","content":"Translate into a concise English document-search query. Preserve names, numbers, years, units, comparisons, and Figure/Table identifiers. Do not answer. English only."},
                {"role":"user","content":text}], max_new_tokens=120)
        for index, case in enumerate(missing, 1):
            plans[case["id"]] = build_query_plan(case["question"], translate)
            save(plan_path, plans)
            print(f"PLAN {index:02d}/{len(missing)} {case['id']}", flush=True)
        del local

    dense = DensePgVectorRetriever(table="day07_advanced_chunks")
    retriever = HybridRRFRetriever(dense, BM25Retriever(chunks), candidate_k=30)
    provider = ClaudeProvider()
    traces = json.loads(trace_path.read_text(encoding="utf-8")) if trace_path.exists() else []
    completed = {row["query_id"] for row in traces if row["status"] != "error"}
    for case in cases:
        if case["id"] in completed:
            print(f"SKIP {case['id']}", flush=True); continue
        started = time.perf_counter(); plan = plans[case["id"]]
        try:
            search_started = time.perf_counter()
            ranked, sets = multi_query_search(retriever, plan["queries"], per_query_k=15, top_k=24)
            search_ms = (time.perf_counter() - search_started) * 1000
            context_ranked = prioritize_query_facets(ranked, sets, depth=5)
            context, ids, pages = pack_page_aware_context(context_ranked, chunks, budget_chars=18000, seed_pages=6)
            result = answer_with_coverage(case["question"], plan["requirements"], context, ids, provider)
            marked=[]
            for row in ranked:
                regions=[i for i,gold in enumerate(case.get("gold",[])) if matches_gold(row,gold)]
                marked.append({**row,"matched_gold_regions":regions,"gold_hit":bool(regions)})
            found={i for row in marked if row["id"] in ids for i in row["matched_gold_regions"]}
            trace={"query_id":case["id"],"split":"test","answerable":case["answerable"],
                "primary_group":case["primary_group"],"status":result["status"],"question":case["question"],
                "answer":result["answer"],"citations":result["citations"],"coverage":result.get("coverage",[]),
                "events":[{"event":"multi_query_search","tool":"multi_query_hybrid_rrf","query_plan":plan,
                    "per_query_top_k":15,"results":marked,"context":context,"context_ids":ids,"context_pages":pages},
                    {"event":result["status"],"raw_model_output":result["raw_model_output"],
                     "format_repair_used":result.get("format_repair_used",False),
                     "original_raw_model_output":result.get("original_raw_model_output")}],
                "retrieval_metrics":({"hit1":bool(marked and marked[0]["gold_hit"]),
                    "evidence_hit3":any(row["gold_hit"] for row in marked[:3]),
                    "complete_context_evidence":len(found)==len(case["gold"]),"found_gold_regions":sorted(found)}
                    if case["answerable"] else None),"usage":result["usage"],
                "timing_ms":{"retrieval":round(search_ms,2),"answer_generation":result["answer_generation_ms"],
                    "total":round((time.perf_counter()-started)*1000,2)},"model":provider.model,
                "provider":"anthropic_compatible_gateway","service_cost_usd":None,
                "cost_note":"Gateway returned tokens but no USD price; no cost was fabricated."}
        except Exception as error:
            trace={"query_id":case["id"],"split":"test","answerable":case["answerable"],
                "primary_group":case["primary_group"],"status":"error","question":case["question"],
                "answer":"","citations":[],"events":[],"error":{"type":type(error).__name__,"message":str(error)},
                "model":provider.model,"provider":"anthropic_compatible_gateway","service_cost_usd":None}
        traces=[row for row in traces if row["query_id"]!=case["id"]]+[trace]; save(trace_path,traces)
        if trace["status"]!="error": completed.add(case["id"])
        print(f"{len(completed):02d}/30 {case['id']} {trace['status']}",flush=True)
    print(json.dumps({"traces":len(traces),"errors":sum(row["status"]=="error" for row in traces)}))

if __name__ == "__main__": main()
