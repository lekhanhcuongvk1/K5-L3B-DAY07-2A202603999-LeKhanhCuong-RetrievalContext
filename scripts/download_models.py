"""Download and verify frozen embedding/agent models in the repo-local cache."""

from __future__ import annotations

import json
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / ".cache" / "huggingface"
MODEL = "bkai-foundation-models/vietnamese-bi-encoder"
REVISION = "84f9d9ada0d1a3c37557398b9ae9fcedcdf40be0"
AGENT_MODEL = "Qwen/Qwen2.5-1.5B-Instruct"
AGENT_REVISION = "989aa7980e4cf806f80c7fef2b1adb7bc71aa306"


def main() -> None:
    CACHE.mkdir(parents=True, exist_ok=True)
    os.environ["HF_HOME"] = str(CACHE)
    os.environ["HF_HUB_CACHE"] = str(CACHE / "hub")

    from huggingface_hub import snapshot_download
    from sentence_transformers import SentenceTransformer

    snapshot = Path(snapshot_download(MODEL, revision=REVISION, cache_dir=CACHE / "hub"))
    agent_snapshot = Path(snapshot_download(
        AGENT_MODEL, revision=AGENT_REVISION, cache_dir=CACHE / "hub"
    ))
    encoder = SentenceTransformer(str(snapshot), device="cpu")
    dimension = encoder.get_embedding_dimension()
    if dimension != 768:
        raise SystemExit(f"Expected 768 dimensions, got {dimension}")
    probe = encoder.encode(["kiểm tra mô hình tiếng Việt"], normalize_embeddings=True)
    if probe.shape != (1, 768):
        raise SystemExit(f"Unexpected probe shape: {probe.shape}")

    result = {
        "provider": "Hugging Face local",
        "embedding_model": MODEL,
        "embedding_revision": REVISION,
        "embedding_license": "Apache-2.0",
        "agent_model": AGENT_MODEL,
        "agent_revision": AGENT_REVISION,
        "agent_license": "Apache-2.0",
        "agent_snapshot_present": agent_snapshot.is_dir(),
        "cache": ".cache/huggingface",
        "dimensions": dimension,
        "probe_shape": list(probe.shape),
    }
    output = ROOT / "artifacts" / "model_validation.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
