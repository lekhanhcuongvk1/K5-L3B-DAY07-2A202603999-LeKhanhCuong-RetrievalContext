"""Run the frozen Advanced pipeline once on all 30 Test questions, resumably."""

from __future__ import annotations

import json
import re
import sys
import time
import unicodedata
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.claude_agent import ClaudeProvider, answer_with_context
from src.local_agent import LocalQwen
from src.retrieval import BM25Retriever, DensePgVectorRetriever, HybridRRFRetriever


OUT = ROOT / "artifacts/cp4/advanced_test/traces.json"
QUERY_OUT = ROOT / "artifacts/cp4/advanced_test/query_translations.json"


def norm(value: str) -> str:
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKD", value).casefold()).strip()


def matches(row: dict, gold: dict) -> bool:
    return row["page"] == gold["physical_pdf_page"] and any(
        norm(term) in norm(row["text"]) for term in gold["verification_terms"]
    )


def pack_rank_interleaved(ranked: list[dict], chunks: list[dict], budget: int = 14000) -> tuple[str, list[str]]:
    seen = {row["id"] for row in ranked}
    ordered = []
    for ranked_row in ranked:
        ordered.append(ranked_row)
        same_page = [row for row in chunks if row["page"] == ranked_row["page"] and row["id"] not in seen]
        ordered.extend(same_page)
        seen.update(row["id"] for row in same_page)
    for ranked_row in ranked:
        adjacent = [row for row in chunks if row["page"] == ranked_row["page"] + 1 and row["id"] not in seen]
        ordered.extend(adjacent)
        seen.update(row["id"] for row in adjacent)
    blocks, ids = [], []
    for row in ordered:
        block = f"[{row['id']} | {row['source']} | trang {row['page']}]\n{row['text']}"
        if len("\n\n".join(blocks + [block])) <= budget:
            blocks.append(block)
            ids.append(row["id"])
    return "\n\n".join(blocks), ids


def save(rows: list[dict]) -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    freeze = json.loads((ROOT / "config/cp3_advanced_freeze.json").read_text(encoding="utf-8"))
    if freeze["test_run_count_at_freeze"] != 0:
        raise SystemExit("Invalid freeze: Test had already been run")
    questions = json.loads((ROOT / "advanced/benchmark/questions.json").read_text(encoding="utf-8"))["questions"]
    test = [row for row in questions if row["split"] == "test"]
    if len(test) != 30:
        raise SystemExit("Expected exactly 30 Advanced Test questions")
    chunks = json.loads((ROOT / "advanced/derived/chunks.json").read_text(encoding="utf-8"))
    translations = json.loads(QUERY_OUT.read_text(encoding="utf-8")) if QUERY_OUT.exists() else {}
    missing = [case for case in test if case["id"] not in translations]
    if missing:
        local = LocalQwen()
        for index, case in enumerate(missing, 1):
            raw = local.generate([
                {"role": "system", "content": "Translate the full Vietnamese question into one English search query. Preserve every proper name, number, year, unit, and Figure/Table/Map identifier. Do not answer. Output English only."},
                {"role": "user", "content": case["question"]},
            ], max_new_tokens=100)
            query = re.sub(r"\s+", " ", raw).strip().strip('"')
            identifiers = re.findall(r"(?:Hình|Bảng|Bản đồ|Figure|Table|Map)\s+[A-Z]?\d+(?:\.\d+)?", case["question"], flags=re.IGNORECASE)
            if identifiers:
                query += " " + " ".join(identifiers).replace("Hình", "Figure").replace("Bảng", "Table").replace("Bản đồ", "Map")
            translations[case["id"]] = {"original_query": case["question"],
                                         "translated_query": query, "raw_model_output": raw}
            QUERY_OUT.parent.mkdir(parents=True, exist_ok=True)
            QUERY_OUT.write_text(json.dumps(translations, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print(f"TRANSLATE {index:02d}/{len(missing)} {case['id']}", flush=True)
        del local
    dense = DensePgVectorRetriever(table="day07_advanced_chunks")
    retriever = HybridRRFRetriever(dense, BM25Retriever(chunks), candidate_k=25)
    provider = ClaudeProvider()
    traces = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else []
    completed = {row["query_id"] for row in traces if row["status"] != "error"}
    for case in test:
        if case["id"] in completed:
            print(f"SKIP {case['id']}", flush=True)
            continue
        started = time.perf_counter()
        query = translations[case["id"]]["translated_query"]
        try:
            search_started = time.perf_counter()
            results = retriever.search(query, filters=None, top_k=10)
            search_ms = (time.perf_counter() - search_started) * 1000
            marked = []
            for row in results:
                regions = [index for index, gold in enumerate(case.get("gold", [])) if matches(row, gold)]
                marked.append({**row, "matched_gold_regions": regions, "gold_hit": bool(regions)})
            context, ids = pack_rank_interleaved(marked, chunks)
            result = answer_with_context(case["question"], context, ids, provider)
            found = {index for row in marked if row["id"] in ids for index in row["matched_gold_regions"]}
            trace = {
                "query_id": case["id"], "split": "test", "answerable": case["answerable"],
                "primary_group": case["primary_group"], "status": result["status"],
                "question": case["question"], "answer": result["answer"], "citations": result["citations"],
                "events": [{"event": "search", "tool": "hybrid_rrf", "query": query,
                            "query_transformed": True, "top_k": 10, "results": marked,
                            "context": context, "context_ids": ids,
                            "context_selection": "rank_interleaved_same_page_then_adjacent_page"},
                           {"event": result["status"], "raw_model_output": result["raw_model_output"]}],
                "retrieval_metrics": ({"hit1": bool(marked and marked[0]["gold_hit"]),
                                       "evidence_hit3": any(row["gold_hit"] for row in marked[:3]),
                                       "complete_context_evidence": len(found) == len(case["gold"]),
                                       "found_gold_regions": sorted(found)} if case["answerable"] else None),
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
                     "primary_group": case["primary_group"], "status": "error",
                     "question": case["question"], "answer": "", "citations": [], "events": [],
                     "error": {"type": type(error).__name__, "message": str(error)},
                     "model": provider.model, "provider": "anthropic_compatible_gateway",
                     "service_cost_usd": None}
        traces = [row for row in traces if row["query_id"] != case["id"]] + [trace]
        save(traces)
        print(f"{len(completed)+1:02d}/30 {case['id']} {trace['status']}", flush=True)
        if trace["status"] != "error":
            completed.add(case["id"])
    print(json.dumps({"traces": len(traces), "errors": sum(row["status"] == "error" for row in traces)}))


if __name__ == "__main__":
    main()
