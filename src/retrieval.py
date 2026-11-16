"""Real Day 7 retrieval adapters with a common, auditable result contract."""

from __future__ import annotations

import math
import os
import re
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Any

import psycopg
from dotenv import load_dotenv
from huggingface_hub import snapshot_download
from sentence_transformers import SentenceTransformer


ROOT = Path(__file__).resolve().parents[1]
EMBEDDING_MODEL = "bkai-foundation-models/vietnamese-bi-encoder"
EMBEDDING_REVISION = "84f9d9ada0d1a3c37557398b9ae9fcedcdf40be0"


def tokenize(text: str) -> list[str]:
    return re.findall(r"\w+", unicodedata.normalize("NFC", text).casefold())


def _matches_filter(chunk: dict[str, Any], filters: dict[str, Any] | None) -> bool:
    if not filters:
        return True
    return all(chunk.get("metadata", {}).get(key) == value for key, value in filters.items())


class DensePgVectorRetriever:
    """Embed queries with the frozen Day 6 encoder and query pgvector exactly."""

    strategy = "dense_pgvector"

    def __init__(self, database_url: str | None = None) -> None:
        load_dotenv(ROOT / ".env")
        self.database_url = database_url or os.getenv(
            "DATABASE_URL", "postgresql://day7:day7_local_only@127.0.0.1:55434/day7_lab"
        )
        cache = ROOT / ".cache" / "huggingface"
        snapshot = snapshot_download(
            EMBEDDING_MODEL,
            revision=EMBEDDING_REVISION,
            cache_dir=cache / "hub",
            local_files_only=True,
        )
        self.encoder = SentenceTransformer(snapshot, device="cpu")

    def search(self, query: str, *, filters: dict[str, Any] | None = None, top_k: int = 3) -> list[dict[str, Any]]:
        if not query.strip() or top_k < 1:
            raise ValueError("query must be non-empty and top_k positive")
        vector = self.encoder.encode([query], normalize_embeddings=True)[0]
        literal = "[" + ",".join(f"{float(value):.9g}" for value in vector) + "]"
        where, params = "", [literal]
        if filters:
            where = "WHERE metadata @> %s::jsonb"
            import json
            params.append(json.dumps(filters, ensure_ascii=False))
        params.extend([literal, top_k])
        sql = f"""
            SELECT chunk_id, text, source_id, source, page, metadata,
                   1 - (embedding <=> %s::vector) AS score
            FROM day07_base_chunks
            {where}
            ORDER BY embedding <=> %s::vector, chunk_id
            LIMIT %s
        """
        with psycopg.connect(self.database_url) as connection, connection.cursor() as cursor:
            cursor.execute(sql, params)
            rows = cursor.fetchall()
        return [
            {"id": row[0], "text": row[1], "source_id": row[2], "source": row[3],
             "page": row[4], "metadata": row[5], "score": float(row[6]),
             "rank": rank, "strategy": self.strategy}
            for rank, row in enumerate(rows, 1)
        ]


class BM25Retriever:
    """Deterministic BM25 baseline over the same 418 chunks."""

    strategy = "bm25"

    def __init__(self, chunks: list[dict[str, Any]], *, k1: float = 1.5, b: float = 0.75) -> None:
        self.chunks = chunks
        self.k1, self.b = k1, b
        self.term_counts = [Counter(tokenize(chunk["text"])) for chunk in chunks]
        self.lengths = [sum(row.values()) for row in self.term_counts]
        self.avg_length = sum(self.lengths) / len(self.lengths)
        df = Counter(term for row in self.term_counts for term in row)
        size = len(chunks)
        self.idf = {term: math.log(1 + (size - count + 0.5) / (count + 0.5)) for term, count in df.items()}

    def search(self, query: str, *, filters: dict[str, Any] | None = None, top_k: int = 3) -> list[dict[str, Any]]:
        terms = tokenize(query)
        if not terms or top_k < 1:
            raise ValueError("query must contain tokens and top_k must be positive")
        ranked = []
        for chunk, counts, length in zip(self.chunks, self.term_counts, self.lengths):
            if not _matches_filter(chunk, filters):
                continue
            score = 0.0
            for term in terms:
                tf = counts.get(term, 0)
                if tf:
                    denominator = tf + self.k1 * (1 - self.b + self.b * length / self.avg_length)
                    score += self.idf.get(term, 0.0) * tf * (self.k1 + 1) / denominator
            if score:
                ranked.append((score, chunk))
        ranked.sort(key=lambda item: (-item[0], item[1]["id"]))
        return [
            {**chunk, "score": score, "rank": rank, "strategy": self.strategy}
            for rank, (score, chunk) in enumerate(ranked[:top_k], 1)
        ]
