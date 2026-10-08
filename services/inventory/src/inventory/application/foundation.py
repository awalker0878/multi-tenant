"""Contract for synthetic infrastructure diagnostics, not product readiness."""

from typing import Protocol


class FoundationProbe(Protocol):
    async def __call__(self) -> bool:
        """Return whether the owned dependency and supported schema are available."""
        ...
