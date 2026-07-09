"""OpenAI provider (async wrapper over a stdlib HTTP call)."""

from __future__ import annotations

import asyncio
import json
import os
import urllib.request

from ..errors import ProviderError
from ..models import Usage
from .base import LLMProvider

_URL = "https://api.openai.com/v1/chat/completions"


class OpenAIProvider(LLMProvider):
    name = "openai"
    default_model = "gpt-4o-mini"

    def __init__(self, api_key: str | None = None, model: str | None = None, timeout: int = 60):
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            raise ProviderError("OPENAI_API_KEY is not set")
        self.model = model or os.environ.get("CONSILIUM_MODEL") or self.default_model
        self.timeout = timeout

    def _call(self, system, prompt, temperature, max_tokens):  # pragma: no cover - network
        payload = {
            "model": self.model, "max_tokens": max_tokens,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}],
            "temperature": 0.3 if temperature is None else temperature,
        }
        req = urllib.request.Request(
            _URL, data=json.dumps(payload).encode(),
            headers={"content-type": "application/json", "authorization": f"Bearer {self.api_key}"})
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            body = json.loads(resp.read())
        text = body["choices"][0]["message"].get("content") or ""
        u = body.get("usage", {})
        return text, Usage(u.get("prompt_tokens", 0), u.get("completion_tokens", 0))

    async def complete(self, system, prompt, *, temperature=None, max_tokens=1024):  # pragma: no cover
        try:
            return await asyncio.to_thread(self._call, system, prompt, temperature, max_tokens)
        except Exception as exc:  # noqa: BLE001
            raise ProviderError(f"OpenAI call failed: {exc}") from exc
