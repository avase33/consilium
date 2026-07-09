"""Anthropic provider (async wrapper over a stdlib HTTP call)."""

from __future__ import annotations

import asyncio
import json
import os
import urllib.request

from ..errors import ProviderError
from ..models import Usage
from .base import LLMProvider

_URL = "https://api.anthropic.com/v1/messages"


class AnthropicProvider(LLMProvider):
    name = "anthropic"
    default_model = "claude-3-5-sonnet-latest"

    def __init__(self, api_key: str | None = None, model: str | None = None, timeout: int = 60):
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ProviderError("ANTHROPIC_API_KEY is not set")
        self.model = model or os.environ.get("CONSILIUM_MODEL") or self.default_model
        self.timeout = timeout

    def _call(self, system, prompt, temperature, max_tokens):  # pragma: no cover - network
        payload = {
            "model": self.model, "max_tokens": max_tokens, "system": system,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3 if temperature is None else temperature,
        }
        req = urllib.request.Request(
            _URL, data=json.dumps(payload).encode(),
            headers={"content-type": "application/json", "x-api-key": self.api_key,
                     "anthropic-version": "2023-06-01"})
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            body = json.loads(resp.read())
        text = "".join(b.get("text", "") for b in body.get("content", []) if b.get("type") == "text")
        u = body.get("usage", {})
        return text, Usage(u.get("input_tokens", 0), u.get("output_tokens", 0))

    async def complete(self, system, prompt, *, temperature=None, max_tokens=1024):  # pragma: no cover
        try:
            return await asyncio.to_thread(self._call, system, prompt, temperature, max_tokens)
        except Exception as exc:  # noqa: BLE001
            raise ProviderError(f"Anthropic call failed: {exc}") from exc
