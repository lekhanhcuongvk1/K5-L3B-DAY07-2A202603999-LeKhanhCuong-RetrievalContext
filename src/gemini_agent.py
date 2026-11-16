"""Official Gemini generateContent adapter used only for provider-error fallback."""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request

from dotenv import load_dotenv


class GeminiProvider:
    def __init__(self) -> None:
        load_dotenv()
        self.api_key = os.environ["GEMINI_API_KEY"]
        self.model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"

    def complete(self, *, system: str, user: str, max_tokens: int = 700):
        endpoint = f"{self.base_url}/models/{urllib.parse.quote(self.model, safe='')}:generateContent"
        payload = json.dumps({
            "systemInstruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": [{"text": user}]}],
            "generationConfig": {
                "temperature": 0,
                "maxOutputTokens": max_tokens,
                "responseMimeType": "application/json",
            },
        }).encode()
        request = urllib.request.Request(
            endpoint, data=payload,
            headers={"x-goog-api-key": self.api_key, "content-type": "application/json"},
        )
        started = time.perf_counter()
        try:
            with urllib.request.urlopen(request, timeout=180) as response:
                result = json.load(response)
        except urllib.error.HTTPError as error:
            body = error.read().decode(errors="replace")[:1000]
            raise RuntimeError(f"Gemini HTTP {error.code}: {body}") from error
        elapsed_ms = (time.perf_counter() - started) * 1000
        candidates = result.get("candidates", [])
        if not candidates:
            raise RuntimeError(f"Gemini returned no candidates: {result.get('promptFeedback')}")
        parts = candidates[0].get("content", {}).get("parts", [])
        text = "".join(part.get("text", "") for part in parts)
        if not text:
            raise RuntimeError("Gemini returned no text content")
        usage = result.get("usageMetadata", {})
        normalized_usage = {
            "input_tokens": usage.get("promptTokenCount", 0),
            "output_tokens": usage.get("candidatesTokenCount", 0),
            "total_tokens": usage.get("totalTokenCount", 0),
        }
        return text.strip(), normalized_usage, elapsed_ms
