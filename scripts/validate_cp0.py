"""Validate the Day 7 submission identity and frozen experiment contract."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXPECTED_REPO = "K5-L3B-DAY07-2A202603999-LeKhanhCuong-RetrievalContext"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def main() -> None:
    require(ROOT.name == EXPECTED_REPO, f"Tên repo phải là {EXPECTED_REPO}")
    required = [
        ROOT / "README.md",
        ROOT / "config" / "experiment_plan.json",
        ROOT / "report" / "individual" / "2A202603999_LeKhanhCuong.md",
    ]
    require(all(path.is_file() for path in required), "Thiếu file submission CP0")

    plan = json.loads(required[1].read_text(encoding="utf-8"))
    require(plan["student"] == {
        "name": "Lê Khánh Cường",
        "student_id": "2A202603999",
        "class": "L3B",
    }, "Thông tin học viên không đúng")
    day6 = plan["day6_source"]
    require(day6["document_count"] == 30 and day6["chunk_count"] == 418,
            "Số liệu nguồn Day 6 không đúng")
    require(day6["embedding_dimensions"] == 768 and day6["distance_metric"] == "cosine",
            "Embedding/index Day 6 không tương thích")

    base = plan["base_benchmark"]
    require(base["dev"]["total"] == 21 and base["test"]["total"] == 9,
            "Benchmark cơ bản không đúng kế hoạch")
    require(len(base["retrieval_methods"]) >= 3,
            "Phải khóa ít nhất ba phương pháp retrieval")
    advanced = plan["advanced_benchmark"]
    require(advanced["enabled"] and advanced["test"]["total"] >= 30,
            "Thử thách nâng cao chưa được bật hoặc thiếu Test")
    require(sum(advanced["test"]["primary_group_minimums"].values()) == 24,
            "Phân bố 24 câu nâng cao có đáp án không đúng")
    require(advanced["test"]["unanswerable"] >= 6,
            "Test nâng cao thiếu câu không đủ evidence")

    policy = plan["integrity_policy"]
    require(policy["select_on"] == "dev_only" and policy["freeze_before_test"],
            "Thiếu chính sách Dev/Test")
    require(not policy["gold_in_agent_or_query"] and not policy["silent_mock_fallback"],
            "Không được đưa gold vào agent hoặc fallback mock")

    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
    require(".env" in gitignore and ".venv/" in gitignore,
            ".gitignore phải chặn secret và môi trường ảo")
    print("CP0 validation OK: identity, Day 6 contract, base/advanced benchmark plan and integrity policy.")


if __name__ == "__main__":
    try:
        main()
    except ValueError as exc:
        raise SystemExit(f"CP0 validation failed: {exc}") from exc
