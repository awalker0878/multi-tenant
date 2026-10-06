"""Owning-service ports; no transport SDK or cross-service source imports."""

from typing import Any, Protocol


class Authority(Protocol):
    def current(self, job: dict[str, Any]) -> dict[str, Any]: ...
    def custody(self) -> str: ...


class Effects(Protocol):
    def execute(self, grant: dict[str, Any]) -> dict[str, Any]: ...
    def reconcile(self, operation: dict[str, Any]) -> dict[str, Any]: ...


class Evidence(Protocol):
    def finalize(
        self, job: dict[str, Any], observations: list[dict[str, Any]]
    ) -> dict[str, Any]: ...


class Alerts(Protocol):
    def deliver(self, event: dict[str, Any]) -> str: ...
