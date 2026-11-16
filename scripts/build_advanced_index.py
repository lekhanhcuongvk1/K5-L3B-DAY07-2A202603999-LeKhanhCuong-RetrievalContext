"""Extract all useful PDF text with page/region provenance and build pgvector index."""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import time
from pathlib import Path

import pymupdf
import psycopg
from dotenv import load_dotenv
from huggingface_hub import snapshot_download
from psycopg.types.json import Jsonb
from sentence_transformers import SentenceTransformer


ROOT = Path(__file__).resolve().parents[1]
PDF = ROOT / "advanced/source/vietnam-2035.pdf"
OUT = ROOT / "advanced/derived/chunks.json"
TABLE = "day07_advanced_chunks"
MODEL = "bkai-foundation-models/vietnamese-bi-encoder"
REVISION = "84f9d9ada0d1a3c37557398b9ae9fcedcdf40be0"


def modality(text: str) -> str:
    upper = text.upper()
    if re.search(r"\b(TABLE|BẢNG)\s+[A-Z0-9]", upper):
        return "table"
    if re.search(r"\b(FIGURE|CHART)\s+[A-Z0-9]", upper):
        return "chart"
    if re.search(r"\b(MAP|DIAGRAM)\s+[A-Z0-9]", upper):
        return "image_or_diagram"
    return "text"


def extract() -> tuple[list[dict], dict]:
    document = pymupdf.open(PDF)
    chunks, skipped = [], []
    for page_index, page in enumerate(document):
        blocks = [block for block in page.get_text("blocks", sort=True) if block[4].strip()]
        if not blocks:
            skipped.append({"physical_pdf_page": page_index + 1, "reason": "no_extractable_text"})
            continue
        current, chars = [], 0
        groups = []
        for block in blocks:
            text = re.sub(r"\s+", " ", block[4]).strip()
            if current and chars + len(text) > 1800:
                groups.append(current)
                current, chars = [], 0
            current.append((block, text))
            chars += len(text) + 1
        if current:
            groups.append(current)
        printed = page.get_text().splitlines()[0].strip() or None
        for group_index, group in enumerate(groups, 1):
            text = "\n".join(item[1] for item in group)
            bbox = [
                round(min(item[0][0] for item in group), 2),
                round(min(item[0][1] for item in group), 2),
                round(max(item[0][2] for item in group), 2),
                round(max(item[0][3] for item in group), 2),
            ]
            digest = hashlib.sha1(text.encode()).hexdigest()[:12]
            chunk_id = f"adv:p{page_index + 1:03d}:b{group_index:02d}:{digest}"
            chunks.append({
                "id": chunk_id, "text": text,
                "source_id": "vietnam-2035-world-bank-2016",
                "source": "advanced/source/vietnam-2035.pdf",
                "page": page_index + 1,
                "metadata": {"printed_page": printed, "bbox_points": bbox,
                             "modality": modality(text), "block_group": group_index},
            })
    stats = {
        "physical_pages": len(document), "indexed_pages": len({row["page"] for row in chunks}),
        "chunk_count": len(chunks), "skipped_pages": skipped,
        "modality_counts": {name: sum(row["metadata"]["modality"] == name for row in chunks)
                            for name in ("text", "table", "chart", "image_or_diagram")},
    }
    return chunks, stats


def vector_literal(values) -> str:
    return "[" + ",".join(f"{float(value):.9g}" for value in values) + "]"


def main() -> None:
    if not PDF.exists():
        raise SystemExit("Run scripts/download_advanced_source.py first")
    chunks, stats = extract()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(chunks, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    cache = ROOT / ".cache/huggingface"
    snapshot = snapshot_download(MODEL, revision=REVISION, cache_dir=cache / "hub", local_files_only=True)
    encoder = SentenceTransformer(snapshot, device="cpu")
    started = time.perf_counter()
    vectors = encoder.encode([row["text"] for row in chunks], batch_size=32,
                             normalize_embeddings=True, show_progress_bar=True)
    stats["embedding_seconds"] = round(time.perf_counter() - started, 3)

    load_dotenv(ROOT / ".env")
    database_url = os.getenv("DATABASE_URL", "postgresql://day7:day7_local_only@127.0.0.1:55434/day7_lab")
    with psycopg.connect(database_url) as connection, connection.cursor() as cursor:
        cursor.execute("CREATE EXTENSION IF NOT EXISTS vector")
        cursor.execute(f"""CREATE TABLE IF NOT EXISTS {TABLE} (
            chunk_id TEXT PRIMARY KEY, text TEXT NOT NULL, source_id TEXT NOT NULL,
            source TEXT NOT NULL, page INTEGER NOT NULL, metadata JSONB NOT NULL,
            embedding vector(768) NOT NULL)""")
        ids = [row["id"] for row in chunks]
        cursor.execute(f"DELETE FROM {TABLE} WHERE NOT (chunk_id = ANY(%s))", (ids,))
        for row, vector in zip(chunks, vectors):
            cursor.execute(f"""INSERT INTO {TABLE}
                (chunk_id,text,source_id,source,page,metadata,embedding)
                VALUES (%s,%s,%s,%s,%s,%s,%s::vector)
                ON CONFLICT (chunk_id) DO UPDATE SET text=EXCLUDED.text, source_id=EXCLUDED.source_id,
                source=EXCLUDED.source, page=EXCLUDED.page, metadata=EXCLUDED.metadata,
                embedding=EXCLUDED.embedding""",
                (row["id"], row["text"], row["source_id"], row["source"], row["page"],
                 Jsonb(row["metadata"]), vector_literal(vector)))
        cursor.execute(f"SELECT COUNT(*) FROM {TABLE}")
        stats["database_rows"] = cursor.fetchone()[0]
        connection.commit()
    stats.update({"table": TABLE, "embedding_model": MODEL, "embedding_revision": REVISION,
                  "dimensions": 768, "metric": "cosine", "service_cost_usd": 0})
    (ROOT / "artifacts/cp3/advanced_index.json").parent.mkdir(parents=True, exist_ok=True)
    (ROOT / "artifacts/cp3/advanced_index.json").write_text(
        json.dumps(stats, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(stats, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
