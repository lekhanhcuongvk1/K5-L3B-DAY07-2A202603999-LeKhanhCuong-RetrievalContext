"""Repack selected Advanced Dev contexts without rerunning retrieval or a model."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def pack(rows: list[dict], budget: int = 14000) -> tuple[str, list[str]]:
    blocks, ids = [], []
    for row in rows:
        block = f"[{row['id']} | {row['source']} | trang {row['page']}]\n{row['text']}"
        if len("\n\n".join(blocks + [block])) <= budget:
            blocks.append(block)
            ids.append(row["id"])
    return "\n\n".join(blocks), ids


def main() -> None:
    path = ROOT / "artifacts/cp3/advanced_dev/advanced_hybrid_translated_wide_traces.json"
    traces = json.loads(path.read_text(encoding="utf-8"))
    chunks = json.loads((ROOT / "advanced/derived/chunks.json").read_text(encoding="utf-8"))
    for trace in traces:
        ranked = trace["results"]
        seen = {row["id"] for row in ranked}
        rows = []
        for ranked_row in ranked:
            rows.append(ranked_row)
            same_page = [row for row in chunks if row["page"] == ranked_row["page"] and row["id"] not in seen]
            rows.extend(same_page)
            seen.update(row["id"] for row in same_page)
        for ranked_row in ranked:
            adjacent = [row for row in chunks if row["page"] == ranked_row["page"] + 1 and row["id"] not in seen]
            rows.extend(adjacent)
            seen.update(row["id"] for row in adjacent)
        trace["context"], trace["context_ids"] = pack(rows)
        trace["context_selection"] = "rank_interleaved_same_page_then_adjacent_page"
    path.write_text(json.dumps(traces, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"repacked": len(traces), "model_calls": 0, "retrieval_calls": 0}))


if __name__ == "__main__":
    main()
