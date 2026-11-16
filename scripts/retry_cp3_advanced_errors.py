"""Retry only recorded provider errors without changing retrieval or prompts."""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.claude_agent import ClaudeProvider, answer_with_context
from src.local_agent import pack_context


def main() -> None:
    path = ROOT / "artifacts/cp3/advanced_agent_dev/traces.json"
    traces = json.loads(path.read_text(encoding="utf-8"))
    selected = {row["query_id"]: row for row in json.loads(
        (ROOT / "artifacts/cp3/advanced_dev/advanced_hybrid_translated_wide_traces.json").read_text(encoding="utf-8")
    )}
    chunks = json.loads((ROOT / "advanced/derived/chunks.json").read_text(encoding="utf-8"))
    provider = ClaudeProvider()
    retried = 0
    for trace in traces:
        if trace["status"] != "error":
            continue
        retrieval = next((row for row in trace.get("events", []) if row.get("event") == "search"), None)
        if retrieval is None:
            source = selected[trace["query_id"]]
            retrieval = {"event": "search", "tool": "hybrid_rrf", "query": source["retrieval_query"],
                         "query_transformed": True, "top_k": 10, "results": source["results"],
                         "context": source["context"], "context_ids": source["context_ids"]}
            trace["events"] = [retrieval]
        if len(retrieval["context"]) > 10000 and retrieval["results"]:
            anchor_page = retrieval["results"][0]["page"]
            compressed_rows = [row for row in chunks if row["page"] in (anchor_page, anchor_page + 1)]
            compressed_context, compressed_ids = pack_context(compressed_rows, 9000)
            retrieval["context"] = compressed_context
            retrieval["context_ids"] = compressed_ids
            retrieval["context_compression"] = "top_ranked_page_plus_next_page"
        result = answer_with_context(trace["question"], retrieval["context"], retrieval["context_ids"], provider)
        trace.update({"status": result["status"], "answer": result["answer"],
                      "citations": result["citations"], "usage": result["usage"],
                      "retry_count": trace.get("retry_count", 0) + 1})
        trace["events"].append({"event": "provider_retry", "attempt": trace["retry_count"]})
        trace["events"].append({"event": result["status"], "raw_model_output": result["raw_model_output"]})
        trace.pop("error", None)
        retried += 1
    path.write_text(json.dumps(traces, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"retried": retried, "remaining_errors": sum(t["status"] == "error" for t in traces)}))


if __name__ == "__main__":
    main()
