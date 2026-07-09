"""Consilium — a production-grade multi-agent corporate research system.

A team of specialized AI agents collaborates to run deep market/company research:

* **Supervisor** plans the work and routes hand-offs between agents.
* **Researcher** gathers evidence with a web-search tool.
* **Analyst** filters and structures raw results into cited findings.
* **Critic** grades the findings and can send the team back for another pass.

They are wired together with a typed, async **state-graph** engine (a
LangGraph-style orchestration layer, with an optional real-LangGraph adapter).
The whole pipeline runs offline on a deterministic mock model + mock search, so
it works with no API keys — drop in Anthropic/OpenAI and a real search backend
for production.
"""

from .version import __version__

__all__ = ["__version__"]
