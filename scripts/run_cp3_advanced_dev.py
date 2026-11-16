"""Evaluate Advanced retrieval on Dev, including explicit query translation."""

from __future__ import annotations

import hashlib
import json
import re
import statistics
import sys
import time
import unicodedata
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.local_agent import LocalQwen, pack_context
from src.retrieval import BM25Retriever, DensePgVectorRetriever, HybridRRFRetriever


def norm(value: str) -> str:
    value = unicodedata.normalize("NFKD", value).casefold()
    return re.sub(r"\s+", " ", value).strip()


def gold_matches(chunk: dict, gold: dict) -> bool:
    if chunk["page"] != gold["physical_pdf_page"]:
        return False
    text = norm(chunk["text"])
    return any(norm(term) in text for term in gold["verification_terms"])


def main() -> None:
    chunks = json.loads((ROOT / "advanced/derived/chunks.json").read_text(encoding="utf-8"))
    benchmark_path = ROOT / "advanced/benchmark/questions.json"
    benchmark = json.loads(benchmark_path.read_text(encoding="utf-8"))["questions"]
    dev = [row for row in benchmark if row["split"] == "dev" and row["answerable"]]
    assert len(dev) == 17

    # Translation is generated from question text only. Gold/evidence is never in
    # the prompt. Save both original and transformed queries for auditability.
    model = LocalQwen()
    translations = {}
    translation_traces = []
    for case in dev:
        raw = model.generate([
            {"role": "system", "content": (
                "Translate the full Vietnamese question into one English search query. Preserve every proper name, "
                "number, year, unit, and Figure/Table/Map identifier. Include all requested conditions. "
                "Do not answer or summarize. Output one line of English only."
            )},
            {"role": "user", "content": case["question"]},
        ], max_new_tokens=80)
        translated = re.sub(r"\s+", " ", raw).strip().strip('"')
        identifiers = re.findall(r"(?:Hình|Bảng|Bản đồ|Figure|Table|Map)\s+[A-Z]?\d+(?:\.\d+)?", case["question"], flags=re.IGNORECASE)
        if identifiers:
            translated += " " + " ".join(identifiers).replace("Hình", "Figure").replace("Bảng", "Table").replace("Bản đồ", "Map")
        if not translated:
            raise ValueError(f"Empty translation for {case['id']}")
        translations[case["id"]] = translated
        translation_traces.append({"query_id": case["id"], "original_query": case["question"],
                                   "translated_query": translated, "raw_model_output": raw})

    dense = DensePgVectorRetriever(table="day07_advanced_chunks")
    bm25 = BM25Retriever(chunks)
    hybrid = HybridRRFRetriever(dense, bm25, candidate_k=15)
    configs = [
        ("advanced_dense_original", dense, False, 3, 5000,
         "Baseline cross-language retrieval with original Vietnamese query."),
        ("advanced_bm25_original", bm25, False, 3, 5000,
         "Lexical control; expected to expose Vietnamese-English vocabulary mismatch."),
        ("advanced_hybrid_original", hybrid, False, 3, 5000,
         "Improvement 1: RRF combines dense and lexical rankings."),
        ("advanced_dense_translated", dense, True, 5, 7000,
         "Improvement 2: local-model English query addresses corpus language mismatch."),
        ("advanced_hybrid_translated", hybrid, True, 5, 7000,
         "Improvement 3: translated query plus RRF and wider context."),
        ("advanced_hybrid_translated_wide", HybridRRFRetriever(dense, bm25, candidate_k=25), True, 10, 14000,
         "Improvement 4: preserve translated constraints and widen context for visual/multi-hop evidence."),
    ]
    output = ROOT / "artifacts/cp3/advanced_dev"
    output.mkdir(parents=True, exist_ok=True)
    (output / "query_translation_traces.json").write_text(
        json.dumps(translation_traces, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    summaries = []
    for config_id, retriever, translated, top_k, budget, hypothesis in configs:
        traces = []
        for case in dev:
            query = translations[case["id"]] if translated else case["question"]
            started = time.perf_counter()
            results = retriever.search(query, filters=None, top_k=top_k)
            elapsed_ms = (time.perf_counter() - started) * 1000
            marked = []
            for row in results:
                matched = [index for index, gold in enumerate(case["gold"]) if gold_matches(row, gold)]
                marked.append({**row, "matched_gold_regions": matched, "gold_hit": bool(matched)})
            context_rows = marked
            if config_id == "advanced_hybrid_translated_wide":
                # Layout extraction can split one table/box across blocks or the
                # next physical page. Add page neighbors selected from retrieval,
                # never from benchmark gold.
                seen = {row["id"] for row in marked}
                page_order = list(dict.fromkeys(row["page"] for row in marked))
                context_rows = []
                for page in page_order:
                    ranked_on_page = [row for row in marked if row["page"] == page]
                    context_rows.extend(ranked_on_page)
                    same_page = [row for row in chunks if row["page"] == page and row["id"] not in seen]
                    context_rows.extend(same_page)
                    seen.update(row["id"] for row in same_page)
                # Adjacent pages are lower priority and only fill remaining budget.
                for page in page_order:
                    adjacent = [row for row in chunks if row["page"] == page + 1 and row["id"] not in seen]
                    context_rows.extend(adjacent)
                    seen.update(row["id"] for row in adjacent)
            context, context_ids = pack_context(context_rows, budget)
            matched_by_id = {row["id"]: row["matched_gold_regions"] for row in marked}
            for row in context_rows[len(marked):]:
                matched_by_id[row["id"]] = [index for index, gold in enumerate(case["gold"]) if gold_matches(row, gold)]
            found_regions = {index for chunk_id in context_ids for index in matched_by_id.get(chunk_id, [])}
            traces.append({
                "query_id": case["id"], "primary_group": case["primary_group"],
                "original_query": case["question"], "retrieval_query": query,
                "query_transformed": translated, "config_id": config_id, "top_k": top_k,
                "results": marked, "context": context, "context_ids": context_ids,
                "hit1": bool(marked and marked[0]["gold_hit"]),
                "evidence_hit3": any(row["gold_hit"] for row in marked[:3]),
                "complete_context_evidence": len(found_regions) == len(case["gold"]),
                "required_gold_regions": len(case["gold"]), "found_gold_regions": sorted(found_regions),
                "elapsed_ms": round(elapsed_ms, 3), "service_cost_usd": 0,
            })
        summary = {
            "config_id": config_id, "split": "dev", "answerable_n": len(traces),
            "method": retriever.strategy, "translated_query": translated, "top_k": top_k,
            "hypothesis": hypothesis, "hit1": sum(row["hit1"] for row in traces),
            "evidence_hit3": sum(row["evidence_hit3"] for row in traces),
            "complete_context_evidence": sum(row["complete_context_evidence"] for row in traces),
            "median_retrieval_ms": round(statistics.median(row["elapsed_ms"] for row in traces), 3),
            "service_cost_usd": 0,
        }
        summaries.append(summary)
        (output / f"{config_id}_traces.json").write_text(
            json.dumps(traces, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    selected = max(summaries, key=lambda row: (
        row["complete_context_evidence"], row["evidence_hit3"], row["hit1"], -row["median_retrieval_ms"]
    ))
    (output / "summary.json").write_text(
        json.dumps({"configs": summaries, "selected": selected["config_id"]}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    freeze = {
        "checkpoint": "CP3", "selection_split": "dev", "test_opened": False,
        "benchmark_sha256": hashlib.sha256(benchmark_path.read_bytes()).hexdigest(),
        "selection_rule": ["complete_context_evidence", "evidence_hit3", "hit1", "lower_median_retrieval_ms"],
        "selected_config": selected, "test_run_count_at_freeze": 0,
    }
    (ROOT / "config/cp3_advanced_freeze.json").write_text(
        json.dumps(freeze, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({"configs": summaries, "selected": selected["config_id"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
