"""Mounted native custody is rechecked before any provider request."""

import json
from dataclasses import replace
from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest
from test_native import Journal, plan_for
from test_native import binding as binding

from lifecycle_worker.application.native import NativeBinding, NativeHeld, digest
from lifecycle_worker.infrastructure.native_runtime import MountedNativeRuntime


@pytest.mark.parametrize(
    "fault", ["shared", "rotation", "changed_runtime", "destination", "missing"]
)
def test_native_runtime_rejects_lost_independence_before_effects(
    binding: NativeBinding, tmp_path: Path, fault: str
) -> None:
    plan = plan_for(binding)
    bound = replace(binding, operation_plan_sha256=digest(plan))
    plan_file, runtime_file = tmp_path / "plan.json", tmp_path / "runtime.json"
    plan_file.write_text(json.dumps(plan))
    connections: dict[str, Any] = {}
    for role in ("writer", "observer"):
        token = tmp_path / (role + ".token")
        token.write_text(role)
        connections[role] = {
            "user_id": str(uuid4()),
            "endpoints": {
                service: {
                    "base_url": "https://native.invalid/" + service,
                    "address": "192.0.2.1",
                    "ca_file": str(tmp_path / "unused.pem"),
                    "token_file": str(token),
                }
                for service in ("identity", "compute", "network", "volume")
            },
        }
    config = {"operation_plan": str(plan_file), **connections}
    if fault == "shared":
        (tmp_path / "observer.token").write_text("writer")
    if fault == "destination":
        connections["observer"]["endpoints"]["compute"]["address"] = "192.0.2.2"
    runtime_file.write_text(json.dumps(config))
    journal = Journal()
    runtime = MountedNativeRuntime(runtime_file, journal, lambda: 100)
    if fault in {"shared", "destination"}:
        with pytest.raises(NativeHeld, match="independent_openstack"):
            runtime.resolve(bound)
    else:
        adapter, _ = runtime.resolve(bound)
        assert adapter.inspect(bound)["native_write_authorized"] is False
        if fault == "rotation":
            (tmp_path / "observer.token").write_text("writer")
        elif fault == "missing":
            (tmp_path / "observer.token").write_text("")
        else:
            connections["writer"]["user_id"] = str(uuid4())
            runtime_file.write_text(json.dumps(config))
        with pytest.raises(NativeHeld):
            adapter.inspect(bound)
        with pytest.raises(NativeHeld):
            adapter.execute(bound, lambda: None)
    assert journal.claimed is False and journal.events == []
