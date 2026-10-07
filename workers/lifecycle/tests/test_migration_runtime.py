"""A v2 migration grant authorizes its exact operation artifact, never a fallback."""

import json
from pathlib import Path
from typing import Any

import pytest

from lifecycle_worker.application.migration_runtime import CommissionedMigrationRuntime
from lifecycle_worker.application.native import NativeBinding, NativeHeld, digest
from lifecycle_worker.application.native_authority import GrantedNativeAuthority


class Client:
    def check(self, stage_grant: dict[str, Any], boundary: str) -> dict[str, Any]:
        return {
            "binding_sha256": digest(stage_grant),
            "epoch": stage_grant["epoch"],
            "boundary": boundary,
            "allowed": True,
            "authority_use": "native_boundary",
            "evaluated_at": 100,
            "expires_at": stage_grant["expires_at"],
        }


def grant() -> dict[str, Any]:
    # Owning worker fixture is isolated from the repository root in package tests.
    g = json.loads((Path(__file__).parent / "fixtures/native-stage-grant-v1.json").read_text())[
        "grant"
    ]
    g.update(schema_version=2, stage="capture")
    g["intent_digest"] = g["native_binding"]["operation_plan_sha256"]
    return g


def test_exact_migration_grant_preserves_tenant_and_operation_bindings() -> None:
    g = grant()
    authority = GrantedNativeAuthority(g, Client(), lambda: 100)
    authority.require_current(authority.binding, "before_api_sequence")
    for key in ("tenant_id", "plan_digest", "operation_plan_sha256"):
        changed = authority.binding.document()
        changed[key] = (
            "a" * 64
            if key.endswith("digest") or key.endswith("sha256")
            else "00000000-0000-4000-8000-000000000099"
        )
        if changed[key] == authority.binding.document()[key]:
            changed[key] = "b" * 64
        with pytest.raises(NativeHeld):
            authority.require_current(NativeBinding.parse(changed), "during_api_sequence")


@pytest.mark.parametrize(
    "field,value", [("schema_version", True), ("stage", "automatic"), ("intent_digest", "a" * 64)]
)
def test_unbound_migration_grant_denied(field: str, value: Any) -> None:
    g = grant()
    g[field] = value
    with pytest.raises(NativeHeld):
        GrantedNativeAuthority(g, Client(), lambda: 100)


def test_registry_never_selects_unregistered_adapter() -> None:
    class Adapter:
        def inspect(self, binding: NativeBinding) -> dict[str, Any]:
            return {}

        def execute(self, binding: NativeBinding, boundary: Any) -> None:
            raise AssertionError("must not execute")

    class Observer:
        def observe(self, binding: NativeBinding, objects: dict[str, Any]) -> dict[str, Any]:
            return {}

    runtime = CommissionedMigrationRuntime({"f" * 64: (Adapter(), Observer())})
    with pytest.raises(NativeHeld, match="not_commissioned"):
        runtime.resolve(NativeBinding.parse(grant()["native_binding"]))
