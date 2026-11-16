"""Embed the self-contained Day 6 snapshot and build the Day 7 pgvector index."""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

import psycopg
from dotenv import load_dotenv
from huggingface_hub import snapshot_download
from psycopg.types.json import Jsonb
from sentence_transformers import SentenceTransformer


ROOT = Path(__file__).resolve().parents[1]
MODEL = "bkai-foundation-models/vietnamese-bi-encoder"
REVISION = "84f9d9ada0d1a3c37557398b9ae9fcedcdf40be0"
TABLE = "day07_base_chunks"


def vector_literal(values) -> str:
    return "[" + ",".join(f"{float(value):.9g}" for value in values) + "]"


def main() -> None:
    load_dotenv(ROOT / ".env")
    database_url = os.getenv(
        "DATABASE_URL",
        "postgresql://day7:day7_local_only@127.0.0.1:55434/day7_lab",
    )
    cache = ROOT / ".cache" / "huggingface"
    os.environ["HF_HOME"] = str(cache)
    os.environ["HF_HUB_CACHE"] = str(cache / "hub")
    snapshot = snapshot_download(
        MODEL, revision=REVISION, cache_dir=cache / "hub", local_files_only=True
    )

    chunks = json.loads((ROOT / "data" / "day6" / "chunks.json").read_text(encoding="utf-8"))
    started = time.perf_counter()
    encoder = SentenceTransformer(snapshot, device="cpu")
    model_seconds = time.perf_counter() - started
    if encoder.get_embedding_dimension() != 768:
        raise SystemExit("Embedding model must produce 768 dimensions")

    embed_started = time.perf_counter()
    vectors = encoder.encode(
        [row["text"] for row in chunks],
        batch_size=32,
        normalize_embeddings=True,
        show_progress_bar=True,
    )
    embedding_seconds = time.perf_counter() - embed_started

    upsert_started = time.perf_counter()
    with psycopg.connect(database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute("CREATE EXTENSION IF NOT EXISTS vector")
            cursor.execute(f"""
                CREATE TABLE IF NOT EXISTS {TABLE} (
                    chunk_id TEXT PRIMARY KEY,
                    text TEXT NOT NULL,
                    source_id TEXT NOT NULL,
                    source TEXT NOT NULL,
                    page TEXT NOT NULL,
                    metadata JSONB NOT NULL,
                    embedding vector(768) NOT NULL
                )
            """)
            ids = [row["id"] for row in chunks]
            cursor.execute(f"DELETE FROM {TABLE} WHERE NOT (chunk_id = ANY(%s))", (ids,))
            for row, vector in zip(chunks, vectors):
                cursor.execute(
                    f"""
                    INSERT INTO {TABLE}
                        (chunk_id, text, source_id, source, page, metadata, embedding)
                    VALUES (%s, %s, %s, %s, %s, %s, %s::vector)
                    ON CONFLICT (chunk_id) DO UPDATE SET
                        text = EXCLUDED.text,
                        source_id = EXCLUDED.source_id,
                        source = EXCLUDED.source,
                        page = EXCLUDED.page,
                        metadata = EXCLUDED.metadata,
                        embedding = EXCLUDED.embedding
                    """,
                    (
                        row["id"], row["text"], row["source_id"], row["source"],
                        row["page"], Jsonb(row["metadata"]), vector_literal(vector),
                    ),
                )
            cursor.execute(f"SELECT COUNT(*) FROM {TABLE}")
            count = cursor.fetchone()[0]
        connection.commit()
    upsert_seconds = time.perf_counter() - upsert_started
    if count != 418:
        raise SystemExit(f"Expected 418 rows, found {count}")

    result = {
        "table": TABLE,
        "rows": count,
        "model": MODEL,
        "revision": REVISION,
        "dimensions": 768,
        "metric": "cosine",
        "search": "exact",
        "model_load_seconds": round(model_seconds, 3),
        "embedding_seconds": round(embedding_seconds, 3),
        "upsert_seconds": round(upsert_seconds, 3),
        "api_cost_usd": 0,
    }
    output = ROOT / "artifacts" / "base_index_metadata.json"
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
