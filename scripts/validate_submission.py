"""Final read-only submission audit for the reported Base and Advanced results."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(relative: str):
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def digest(relative: str) -> str:
    return hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()


def main() -> None:
    base = load("artifacts/cp4/base_test/summary.json")
    assert all(row["passed"] == 9 for row in base["configs"].values())

    pipeline_freeze = load("config/improved_advanced_freeze.json")
    for relative, expected in pipeline_freeze["files_sha256"].items():
        assert digest(relative) == expected, f"pipeline freeze mismatch: {relative}"

    benchmark_freeze = load("advanced/benchmark_v2/freeze.json")
    assert digest("advanced/benchmark_v2/questions.json") == benchmark_freeze["questions_sha256"]
    assert benchmark_freeze["question_count"] == 30

    traces = load("artifacts/improvement/independent_test_v2/traces.json")
    reviews = load("artifacts/improvement/independent_test_v2/reviews.json")
    summary = load("artifacts/improvement/independent_test_v2/summary.json")
    assert len(traces) == len(reviews) == 30
    assert {row["query_id"] for row in traces} == {f"N{number:02d}" for number in range(1, 31)}
    assert all(row["status"] != "error" for row in traces)
    assert sum(row["pass"] for row in reviews) == summary["passed"] == 25
    assert summary["bonus_threshold_met"] is False

    report = (ROOT / "report/individual/2A202603999_LeKhanhCuong.md").read_text(encoding="utf-8")
    assert "25/30" in report and "không tuyên bố đạt bonus" in report
    assert not re.search(r"sẽ được (?:bổ sung|hoàn thiện|ghi)", report, flags=re.IGNORECASE)

    tracked = subprocess.check_output(["git", "ls-files"], cwd=ROOT, text=True).splitlines()
    assert ".env" not in tracked
    assert not any(path.endswith((".pem", ".key")) for path in tracked)
    print(json.dumps({"submission": "PASS", "base_test": "9/9", "advanced_test_v2": "25/30", "bonus": False}))


if __name__ == "__main__":
    main()
