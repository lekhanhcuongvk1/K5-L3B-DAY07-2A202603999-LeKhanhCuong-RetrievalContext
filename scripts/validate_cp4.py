from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(relative: str):
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def main() -> None:
    base = load("artifacts/cp4/base_test/traces.json")
    base_reviews = load("artifacts/cp4/base_test/reviews.json")
    advanced = load("artifacts/cp4/advanced_test/traces.json")
    advanced_reviews = load("artifacts/cp4/advanced_test/reviews.json")
    advanced_summary = load("artifacts/cp4/advanced_test/summary.json")

    assert len(base) == 18 and len(base_reviews) == 18
    assert {(row["config_id"], row["query_id"]) for row in base} == {
        (config, f"B{number}")
        for config in ("dense_baseline", "bm25_selected")
        for number in range(22, 31)
    }
    assert all(row["split"] == "test" and row["status"] != "error" for row in base)
    assert all(row["pass"] for row in base_reviews)

    assert len(advanced) == 30 and len(advanced_reviews) == 30
    assert {row["query_id"] for row in advanced} == {f"A{number}" for number in range(21, 51)}
    assert all(row["split"] == "test" and row["status"] != "error" for row in advanced)
    assert sum(row["pass"] for row in advanced_reviews) == 22
    assert advanced_summary["passed"] == 22
    assert advanced_summary["bonus_threshold_met"] is False

    tracked = subprocess.check_output(["git", "ls-files"], cwd=ROOT, text=True).splitlines()
    forbidden = {".env", "models", "data/advanced/vietnam-2035.pdf"}
    assert not forbidden.intersection(tracked)
    print(json.dumps({"cp4": "PASS", "base_traces": 18, "advanced_traces": 30, "advanced_passed": 22}))


if __name__ == "__main__":
    main()
