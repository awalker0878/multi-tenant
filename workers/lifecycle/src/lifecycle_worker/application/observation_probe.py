"""Independent observation producer port; it grants no native write authority."""

from typing import Any, Protocol


class ObservationProbe(Protocol):
    def observe(self, tenant: str, caller: str, body: dict[str, Any]) -> dict[str, Any]: ...
