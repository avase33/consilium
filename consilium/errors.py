"""Exception hierarchy for Consilium."""

from __future__ import annotations


class ConsiliumError(Exception):
    """Base class for all Consilium errors."""


class ConfigError(ConsiliumError):
    """Invalid or missing configuration."""


class ProviderError(ConsiliumError):
    """An LLM provider failed or is misconfigured."""


class ToolError(ConsiliumError):
    """A tool failed. Agents catch these and feed them back to the model."""


class SearchError(ToolError):
    """The web-search backend failed."""


class GraphError(ConsiliumError):
    """The orchestration graph is malformed or a node failed fatally."""


class MaxIterationsReached(ConsiliumError):
    """The research loop hit its iteration budget without passing review."""
