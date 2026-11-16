"""Create a self-contained Day 7 data snapshot from the permitted Day 6 output."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-repo", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=ROOT / "data" / "day6")
    args = parser.parse_args()
    source = args.source_repo.resolve()
    output = args.output.resolve()

    required = [
        source / "data" / "manifest.json",
        source / "data" / "vi_wikipedia_computing" / "source_catalog.json",
        source / "results" / "chunks_B.jsonl",
    ]
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise SystemExit(f"Day 6 source is incomplete: {missing}")

    manifest = json.loads(required[0].read_text(encoding="utf-8"))
    if manifest["summary"]["content_unit_count"] != 30:
        raise SystemExit("Expected the frozen 30-unit Day 6 corpus")

    corpus_out = output / "corpus"
    corpus_out.mkdir(parents=True, exist_ok=True)
    for old in corpus_out.glob("*.txt"):
        old.unlink()
    for item in manifest["files"]:
        source_file = source / item["path"]
        if not source_file.is_file():
            raise SystemExit(f"Missing Day 6 source file: {source_file}")
        shutil.copy2(source_file, corpus_out / source_file.name)

    shutil.copy2(required[0], output / "manifest.json")
    shutil.copy2(required[1], output / "source_catalog.json")

    chunks = []
    for line_number, line in enumerate(required[2].read_text(encoding="utf-8").splitlines(), 1):
        raw = json.loads(line)
        unit_id = raw["unit_id"]
        local_source = f"data/day6/corpus/{Path(raw['source']).name}"
        metadata = {
            **raw.get("metadata", {}),
            "unit_id": unit_id,
            "char_start": raw["char_start"],
            "char_end": raw["char_end"],
            "day6_chunk_id": raw["chunk_id"],
        }
        chunks.append({
            "id": raw["chunk_id"],
            "text": raw["text"],
            "source_id": raw["document_id"],
            "source": local_source,
            "page": unit_id,
            "metadata": metadata,
        })
        if not chunks[-1]["text"].strip():
            raise SystemExit(f"Empty chunk at line {line_number}")

    if len(chunks) != 418 or len({row["id"] for row in chunks}) != 418:
        raise SystemExit("Expected 418 unique strategy-B chunks")
    (output / "chunks.json").write_text(
        json.dumps(chunks, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"Imported 30 source files and {len(chunks)} chunks into {output}")


if __name__ == "__main__":
    main()
