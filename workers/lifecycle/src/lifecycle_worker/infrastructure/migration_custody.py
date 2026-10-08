"""Receipt lookup ports shared by capture, transfer, conversion and import."""

from typing import Any, Protocol

from lifecycle_worker.application.native import NativeBinding


class CaptureCustody(Protocol):
    def capture(self, binding: NativeBinding, plan_sha256: str) -> dict[str, Any]: ...


class ArtifactCustody(Protocol):
    def artifact(self, binding: NativeBinding, plan_sha256: str, kind: str) -> dict[str, Any]: ...
