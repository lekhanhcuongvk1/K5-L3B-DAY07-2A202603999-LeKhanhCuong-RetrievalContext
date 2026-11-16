"""Quality gate for CP1: standalone sources, indexes and frozen benchmarks."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
from collections import Counter
from pathlib import Path

import psycopg
from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[1]


def load(path: str):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def digest(path: str) -> str:
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()


def main() -> None:
    chunks = load("data/day6/chunks.json")
    assert len(chunks) == 418
    assert len({row["id"] for row in chunks}) == 418
    assert all(set(("id", "text", "source_id", "source", "page", "metadata")) <= row.keys() for row in chunks)
    assert all(not Path(row["source"]).is_absolute() for row in chunks)

    model = load("artifacts/model_validation.json")
    index = load("artifacts/base_index_metadata.json")
    assert model["dimensions"] == index["dimensions"] == 768
    assert index["rows"] == 418 and index["table"] == "day07_base_chunks"
    assert index["search"] == "exact" and index["api_cost_usd"] == 0
    load_dotenv(ROOT / ".env")
    database_url = os.getenv(
        "DATABASE_URL", "postgresql://day7:day7_local_only@127.0.0.1:55434/day7_lab"
    )
    with psycopg.connect(database_url) as connection, connection.cursor() as cursor:
        cursor.execute("SELECT COUNT(*), MIN(vector_dims(embedding)), MAX(vector_dims(embedding)) FROM day07_base_chunks")
        count, min_dims, max_dims = cursor.fetchone()
        assert (count, min_dims, max_dims) == (418, 768, 768)
        cursor.execute("SELECT embedding::text FROM day07_base_chunks ORDER BY chunk_id LIMIT 1")
        probe = cursor.fetchone()[0]
        cursor.execute("SELECT chunk_id FROM day07_base_chunks ORDER BY embedding <=> %s::vector LIMIT 3", (probe,))
        assert len(cursor.fetchall()) == 3

    base = load("benchmark/base_questions.json")
    base_freeze = load("benchmark/base_freeze.json")
    assert digest("benchmark/base_questions.json") == base_freeze["questions_sha256"]
    base_counts = Counter((q["split"], q["answerable"]) for q in base["questions"])
    assert base_counts == Counter({("dev", True): 18, ("dev", False): 3, ("test", True): 6, ("test", False): 3})
    chunk_text = "\n".join(row["text"] for row in chunks)
    for question in base["questions"]:
        if question["answerable"]:
            assert all(gold["evidence"] in chunk_text for gold in question["gold"])

    advanced = load("advanced/benchmark/questions.json")
    advanced_freeze = load("advanced/benchmark/freeze.json")
    assert digest("advanced/benchmark/questions.json") == advanced_freeze["sha256"]
    counts = Counter((q["split"], q["primary_group"]) for q in advanced["questions"])
    expected_test = {"table": 6, "image_or_diagram": 5, "chart": 5, "multi_hop": 4, "text": 4, "unanswerable": 6}
    assert {group: counts[("test", group)] for group in expected_test} == expected_test
    assert sum(q["split"] == "dev" for q in advanced["questions"]) == 20
    assert sum(q["split"] == "test" for q in advanced["questions"]) == 30
    for question in advanced["questions"]:
        if question["answerable"]:
            assert all(gold["bbox_points"] and gold["evidence_excerpt"] for gold in question["gold"])
            if question["primary_group"] == "multi_hop":
                assert len(question["gold"]) >= 2

    ignored = subprocess.run(
        ["git", "check-ignore", "advanced/source/vietnam-2035.pdf", ".cache/huggingface"],
        cwd=ROOT, check=True, capture_output=True, text=True,
    ).stdout
    assert "advanced/source/vietnam-2035.pdf" in ignored and ".cache" in ignored
    tracked = subprocess.run(["git", "ls-files"], cwd=ROOT, check=True, capture_output=True, text=True).stdout
    assert "advanced/source/vietnam-2035.pdf" not in tracked
    print("CP1 quality gate: PASS")


if __name__ == "__main__":
    main()
