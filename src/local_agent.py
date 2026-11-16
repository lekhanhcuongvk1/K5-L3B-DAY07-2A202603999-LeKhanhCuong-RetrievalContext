"""Local model controller and traceable one-tool agent for CP2."""

from __future__ import annotations

import re
import time
import unicodedata
from pathlib import Path
from typing import Any

from huggingface_hub import snapshot_download
from transformers import AutoModelForCausalLM, AutoTokenizer


ROOT = Path(__file__).resolve().parents[1]
MODEL = "Qwen/Qwen2.5-1.5B-Instruct"
REVISION = "989aa7980e4cf806f80c7fef2b1adb7bc71aa306"
ABSTENTION = "Không đủ bằng chứng trong tài liệu để trả lời."


class LocalQwen:
    """A real local model: it writes the search query and grounded final answer."""

    def __init__(self) -> None:
        cache = ROOT / ".cache" / "huggingface"
        snapshot = snapshot_download(MODEL, revision=REVISION, cache_dir=cache / "hub", local_files_only=True)
        self.tokenizer = AutoTokenizer.from_pretrained(snapshot, local_files_only=True)
        self.model = AutoModelForCausalLM.from_pretrained(
            snapshot, local_files_only=True, torch_dtype="auto", low_cpu_mem_usage=True
        )

    def generate(self, messages: list[dict[str, str]], *, max_new_tokens: int) -> str:
        prompt = self.tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        inputs = self.tokenizer(prompt, return_tensors="pt")
        outputs = self.model.generate(
            **inputs, max_new_tokens=max_new_tokens, do_sample=False,
            repetition_penalty=1.05, pad_token_id=self.tokenizer.eos_token_id,
        )
        generated = outputs[0, inputs["input_ids"].shape[1]:]
        return self.tokenizer.decode(generated, skip_special_tokens=True).strip()

    def make_query(self, question: str) -> str:
        result = self.generate([
            {"role": "system", "content": "Bạn tạo truy vấn tìm kiếm ngắn bằng tiếng Việt. Chỉ xuất truy vấn, không giải thích."},
            {"role": "user", "content": question},
        ], max_new_tokens=64)
        query = result.splitlines()[0].strip().strip('"')
        if not query:
            raise ValueError("Local model returned an empty retrieval query")
        return query

    def answer(self, question: str, context: str, allowed_ids: list[str]) -> tuple[str, list[str], str]:
        aliases = {f"E{index}": chunk_id for index, chunk_id in enumerate(allowed_ids, 1)}
        model_context = context
        for alias, chunk_id in aliases.items():
            model_context = model_context.replace(f"[{chunk_id} |", f"[{alias} |")
        ids = ", ".join(aliases)
        raw = self.generate([
            {"role": "system", "content": (
                "You are a strict evidence reader. Never use knowledge outside CONTEXT. "
                "Your entire output MUST use exactly one of these formats:\n"
                "SUPPORTED: E1\nANSWER: short Vietnamese answer\n"
                "or\nINSUFFICIENT\n"
                f"Valid evidence labels: {ids}. Use SUPPORTED only when the cited evidence directly answers the question."
            )},
            {"role": "user", "content": f"CONTEXT:\n{model_context}\n\nCÂU HỎI:\n{question}\n\nKẾT QUẢ:"},
        ], max_new_tokens=220)
        support_line = re.search(r"SUPPORTED\s*:\s*([^\n]+)", raw, flags=re.IGNORECASE)
        used_aliases = [] if not support_line else [
            item for item in dict.fromkeys(re.findall(r"E\d+", support_line.group(1), flags=re.IGNORECASE))
            if item.upper() in aliases
        ]
        used_aliases = [item.upper() for item in used_aliases]
        answer_match = re.search(r"ANSWER\s*:\s*(.+)", raw, flags=re.IGNORECASE | re.DOTALL)
        if used_aliases and not answer_match:
            remainder = raw[support_line.end():].strip() if support_line else ""
            if remainder and "INSUFFICIENT" not in remainder.upper():
                answer_match = re.match(r"(.*)", remainder, flags=re.DOTALL)
        # Small local models occasionally omit the requested label while copying a
        # supported answer verbatim.  Accept only an exact normalized substring
        # match in one retrieved block; this is auditable citation attribution,
        # not a semantic or silent fallback.
        if support_line and not used_aliases and not answer_match:
            candidate = support_line.group(1).strip()
            def normalize(value: str) -> str:
                value = re.sub(r"\s+", " ", unicodedata.normalize("NFKC", value).casefold()).strip()
                return re.sub(r"\s+([.,;:!?])", r"\1", value)
            for alias in aliases:
                block_match = re.search(
                    rf"\[{alias}\s*\|.*?\]\n(.*?)(?=\n\n\[E\d+\s*\||\Z)",
                    model_context, flags=re.DOTALL,
                )
                if block_match and normalize(candidate) in normalize(block_match.group(1)):
                    used_aliases = [alias]
                    answer_match = re.match(r"(.*)", candidate, flags=re.DOTALL)
                    break
        citations = [aliases[item] for item in used_aliases]
        if not citations or not answer_match:
            return ABSTENTION, [], raw
        answer_text = answer_match.group(1).strip()
        answer = answer_text + " " + " ".join(f"[{aliases[alias]}]" for alias in used_aliases)
        return answer, citations, raw


def pack_context(results: list[dict[str, Any]], budget_chars: int) -> tuple[str, list[str]]:
    blocks, ids = [], []
    for row in results:
        block = f"[{row['id']} | {row['source']} | trang {row['page']}]\n{row['text']}"
        candidate = "\n\n".join(blocks + [block])
        if len(candidate) <= budget_chars:
            blocks.append(block)
            ids.append(row["id"])
    return "\n\n".join(blocks), ids


def run(question: str, model: LocalQwen, retriever: Any, *, filters: dict[str, Any] | None = None,
        top_k: int = 3, budget_chars: int = 3600, rewrite_query: bool = True) -> dict[str, Any]:
    started = time.perf_counter()
    query_started = time.perf_counter()
    query = model.make_query(question) if rewrite_query else question
    query_ms = (time.perf_counter() - query_started) * 1000
    search_started = time.perf_counter()
    results = retriever.search(query, filters=filters, top_k=top_k)
    search_ms = (time.perf_counter() - search_started) * 1000
    context, ids = pack_context(results, budget_chars)
    if not context:
        answer, citations, raw = ABSTENTION, [], ""
        answer_ms = 0.0
    else:
        answer_started = time.perf_counter()
        answer, citations, raw = model.answer(question, context, ids)
        answer_ms = (time.perf_counter() - answer_started) * 1000
    status = "answered" if citations else "abstain"
    return {
        "status": status,
        "question": question,
        "answer": answer,
        "citations": citations,
        "events": [{
            "event": "search", "tool": retriever.strategy, "query": query,
            "query_transformed": rewrite_query, "filter": filters, "top_k": top_k, "results": results,
            "context": context, "context_ids": ids,
        }, {"event": status, "raw_model_output": raw}],
        "timing_ms": {"query_generation": round(query_ms, 2), "retrieval": round(search_ms, 2),
                      "answer_generation": round(answer_ms, 2),
                      "total": round((time.perf_counter() - started) * 1000, 2)},
        "model": {"name": MODEL, "revision": REVISION, "provider": "local_huggingface"},
        "service_cost_usd": 0,
    }
