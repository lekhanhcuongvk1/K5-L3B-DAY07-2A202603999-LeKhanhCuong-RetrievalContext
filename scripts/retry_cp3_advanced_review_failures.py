"""Rerun only manually identified Dev failures after global context repacking."""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.claude_agent import ClaudeProvider, answer_with_context


TARGETS = {"A13"}


def main() -> None:
    trace_path = ROOT / "artifacts/cp3/advanced_agent_dev/traces.json"
    traces = json.loads(trace_path.read_text(encoding="utf-8"))
    retrieval = {row["query_id"]: row for row in json.loads(
        (ROOT / "artifacts/cp3/advanced_dev/advanced_hybrid_translated_wide_traces.json").read_text(encoding="utf-8")
    )}
    chunks = json.loads((ROOT / "advanced/derived/chunks.json").read_text(encoding="utf-8"))
    provider = ClaudeProvider()
    rerun = 0
    for trace in traces:
        if trace["query_id"] not in TARGETS:
            continue
        source = retrieval[trace["query_id"]]
        top_pages = list(dict.fromkeys(row["page"] for row in source["results"]))[:3]
        focused = [row for row in chunks if row["page"] in top_pages]
        blocks, ids = [], []
        for row in focused:
            block = f"[{row['id']} | {row['source']} | trang {row['page']}]\n{row['text']}"
            if len("\n\n".join(blocks + [block])) <= 18000:
                blocks.append(block)
                ids.append(row["id"])
        context = "\n\n".join(blocks)
        result = answer_with_context(trace["question"], context, ids, provider)
        trace.update({"status": result["status"], "answer": result["answer"],
                      "citations": result["citations"], "usage": result["usage"],
                      "dev_failure_rerun": True})
        trace["events"] = [
            {"event": "search", "tool": "hybrid_rrf", "query": source["retrieval_query"],
             "query_transformed": True, "top_k": 10, "results": source["results"],
             "context": context, "context_ids": ids,
             "context_selection": "all_blocks_from_top_three_ranked_pages"},
            {"event": result["status"], "raw_model_output": result["raw_model_output"]},
        ]
        rerun += 1
        print(f"{trace['query_id']} {trace['status']}", flush=True)
    trace_path.write_text(json.dumps(traces, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"rerun": rerun, "targets": sorted(TARGETS)}))


if __name__ == "__main__":
    main()
