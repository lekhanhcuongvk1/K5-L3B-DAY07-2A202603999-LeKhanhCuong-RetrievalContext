"""Summarize human-reviewed CP3 Base and Advanced Dev runs."""

from __future__ import annotations

import json
import statistics
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def summarize(folder: Path) -> dict:
    traces = json.loads((folder / "traces.json").read_text(encoding="utf-8"))
    reviews = json.loads((folder / "reviews.json").read_text(encoding="utf-8"))
    flags = [flag for review in reviews for flag in review["citation_support"]]
    usage = [trace.get("usage", {}) for trace in traces]
    times = [trace.get("timing_ms", {}).get("total") for trace in traces]
    times = [value for value in times if value is not None]
    return {
        "split": "dev", "n": len(traces), "passed": sum(row["pass"] for row in reviews),
        "pass_rate": round(sum(row["pass"] for row in reviews) / len(reviews), 4),
        "answered": sum(row["status"] == "answered" for row in traces),
        "abstained": sum(row["status"] == "abstain" for row in traces),
        "errors": sum(row["status"] == "error" for row in traces),
        "tool_use": sum(any(event.get("event") == "search" for event in row["events"]) for row in traces),
        "valid_citations": sum(flags), "total_citations": len(flags),
        "citation_validity": round(sum(flags) / len(flags), 4) if flags else None,
        "input_tokens": sum(row.get("input_tokens", 0) + row.get("cache_read_input_tokens", 0) for row in usage),
        "output_tokens": sum(row.get("output_tokens", 0) for row in usage),
        "median_total_ms": round(statistics.median(times), 2) if times else None,
        "service_cost_usd": None,
        "cost_note": "Gateway returned token usage but no USD price; no cost was fabricated.",
        "human_reviewed": True, "test_opened": False,
    }


def main() -> None:
    base_dir = ROOT / "artifacts/cp3/base_agent_claude_dev"
    advanced_dir = ROOT / "artifacts/cp3/advanced_agent_dev"
    base, advanced = summarize(base_dir), summarize(advanced_dir)
    (base_dir / "summary.json").write_text(json.dumps(base, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (advanced_dir / "summary.json").write_text(json.dumps(advanced, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"base": base, "advanced": advanced}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
