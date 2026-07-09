"""Deterministic, offline mock LLM.

Produces plausible, reproducible prose for each agent task so the entire research
pipeline runs — and tests pass — without any API key. It keys off task markers
the agents embed in their prompts (``[[TASK:...]]``).
"""

from __future__ import annotations

import re

from ..models import Usage
from .base import LLMProvider

_TASK = re.compile(r"\[\[TASK:([A-Z_]+)\]\]")
_TOPIC = re.compile(r"\[\[TOPIC:(.*?)\]\]", re.DOTALL)


def _usage(prompt: str, out: str) -> Usage:
    return Usage(prompt_tokens=max(1, len(prompt) // 4), completion_tokens=max(1, len(out) // 4))


_SUBTOPIC_TEMPLATES = [
    "Market size, growth rate and key segments",
    "Competitive landscape and main players",
    "Business model, pricing and unit economics",
    "Recent developments, funding and strategic moves",
    "Risks, regulation and headwinds",
    "Technology, product and differentiation",
]


class MockLLM(LLMProvider):
    name = "mock"
    default_model = "consilium-mock-1"

    async def complete(self, system, prompt, *, temperature=None, max_tokens=1024):
        task = (_TASK.search(prompt) or _TASK.search(system))
        task = task.group(1) if task else "GENERIC"
        topic_m = _TOPIC.search(prompt) or _TOPIC.search(system)
        topic = topic_m.group(1).strip() if topic_m else "the subject"

        if task == "PLAN":
            n = 4
            m = re.search(r"\[\[N:(\d+)\]\]", prompt)
            if m:
                n = int(m.group(1))
            lines = [f"{i+1}. {t} for {topic}" for i, t in enumerate(_SUBTOPIC_TEMPLATES[:n])]
            out = "\n".join(lines)
        elif task == "SUMMARY":
            out = (
                f"This report synthesizes the current state of {topic}. The evidence points to a "
                f"market that is growing but competitive, with several established players and a few "
                f"fast-moving challengers. Key opportunities lie in differentiation and unit economics, "
                f"while the principal risks are regulatory pressure and execution. Overall the outlook "
                f"is cautiously positive, contingent on the factors detailed below."
            )
        elif task == "SECTION":
            out = (
                "The evidence in this area is consistent across the retrieved sources. The main signal "
                "is a clear direction of travel supported by multiple independent references, with a "
                "few open questions flagged for further validation."
            )
        elif task == "CRITIQUE":
            out = "Coverage is reasonable; consider adding more quantitative evidence and primary sources."
        else:
            out = f"Analysis of {topic}: the available evidence supports a measured, well-cited conclusion."
        return out, _usage(prompt, out)
