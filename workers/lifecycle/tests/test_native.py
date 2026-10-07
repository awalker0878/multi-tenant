"""P07 software boundaries using synthetic plans/providers, never native qualification."""

import copy
import hashlib
import json
import os
import sys
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest

from lifecycle_worker.application.native import (
    NativeBinding,
    NativeHeld,
    ProcessResult,
    SavedPlanExecution,
    decode,
    digest,
)
from lifecycle_worker.infrastructure.native_files import protected_read, verify_bundle
from lifecycle_worker.infrastructure.openstack_readback import OpenStackReadback, state_objects
from lifecycle_worker.infrastructure.terraform import TerraformSavedPlan, run, validate_plan


@pytest.fixture
def binding() -> NativeBinding:
    values: dict[str, Any] = {
        k: str(uuid4())
        for k in (
            "tenant_id",
            "site_id",
            "project_id",
            "resource_id",
            "job_id",
            "operation_id",
            "attempt_id",
            "campaign_id",
            "executor_id",
            "epoch",
            "state_lineage",
        )
    }
    return NativeBinding.parse(
        values
        | {
            "plan_digest": "a" * 64,
            "bundle_sha256": "b" * 64,
            "workspace": "default",
            "state_serial": 1,
            "expires_at": 200,
        }
    )


def resources(binding: NativeBinding) -> dict[str, Any]:
    metadata = {"product_tenant_id": binding.tenant_id, "product_resource_id": binding.resource_id}
    return {
        "openstack_compute_instance_v2.application": {
            "kind": "server",
            "expected": {"name": "application", "flavor_id": "small", "metadata": metadata},
        },
        "openstack_networking_port_v2.quarantine": {
            "kind": "port",
            "expected": {
                "tenant_id": binding.project_id,
                "description": f"product:{binding.tenant_id}:{binding.resource_id}",
                "admin_state_up": False,
                "port_security_enabled": True,
                "security_group_ids": [str(uuid4())],
                "network_id": str(uuid4()),
                "fixed_ip": [{"subnet_id": str(uuid4()), "ip_address": "192.0.2.8"}],
            },
        },
        "openstack_blockstorage_volume_v3.root": {
            "kind": "volume",
            "expected": {
                "name": "root",
                "size": 10,
                "volume_type": "encrypted",
                "metadata": metadata,
            },
        },
    }


def plan_for(expected: dict[str, Any]) -> dict[str, Any]:
    return {
        "format_version": "1.2",
        "terraform_version": "1.16.0",
        "errored": False,
        "applyable": True,
        "complete": True,
        "configuration": {"root_module": {}},
        "resource_changes": [
            {
                "address": address,
                "mode": "managed",
                "type": address.split(".")[0],
                "provider_name": "registry.terraform.io/terraform-provider-openstack/openstack",
                "change": {
                    "actions": ["create"],
                    "before": None,
                    "after": contract["expected"],
                    "after_unknown": {"id": True},
                },
            }
            for address, contract in expected.items()
        ],
    }


@pytest.mark.parametrize(
    "raw", [b'{"a":1,"a":2}', b'{"a":NaN}', b'{"a":Infinity}', b"[]", b"{} " * 10]
)
def test_strict_native_documents(raw: bytes) -> None:
    with pytest.raises(NativeHeld):
        decode(raw)


def test_bindings_are_exact_and_accept_keystone_hex_ids(binding: NativeBinding) -> None:
    assert NativeBinding.parse(binding.document()) == binding
    document = binding.document() | {"project_id": uuid4().hex}
    assert NativeBinding.parse(document).project_id == document["project_id"]
    with pytest.raises(NativeHeld):
        NativeBinding.parse(document | {"native_write_authorized": True})


@pytest.mark.parametrize(
    "field,value",
    [
        ("state_serial", True),
        ("state_serial", -1),
        ("expires_at", False),
        ("workspace", "../other"),
        ("project_id", "*"),
        ("plan_digest", "A" * 64),
    ],
)
def test_invalid_bindings(binding: NativeBinding, field: str, value: Any) -> None:
    with pytest.raises(NativeHeld):
        NativeBinding.parse(binding.document() | {field: value})


def test_plan_accepts_only_reviewed_quarantined_creates(binding: NativeBinding) -> None:
    expected = resources(binding)
    validate_plan(plan_for(expected), expected, binding)


@pytest.mark.parametrize(
    "mutation",
    [
        "delete",
        "replace",
        "update",
        "unlisted",
        "duplicate",
        "foreign_provider",
        "import",
        "moved",
        "deposed",
        "deferred",
        "drift",
        "incomplete",
        "errored",
        "provisioner",
        "unknown_metadata",
        "changed_field",
        "wrong_project",
        "active_port",
        "unsecured_port",
        "missing_security_group",
        "ownership",
        "new_format",
    ],
)
def test_plan_denials(binding: NativeBinding, mutation: str) -> None:
    expected = resources(binding)
    plan = copy.deepcopy(plan_for(expected))
    first = plan["resource_changes"][0]
    if mutation in {"delete", "replace", "update"}:
        first["change"]["actions"] = ["create", "delete"] if mutation == "replace" else [mutation]
    elif mutation == "unlisted":
        first["address"] += "_unowned"
    elif mutation == "duplicate":
        plan["resource_changes"][1] = copy.deepcopy(first)
    elif mutation == "foreign_provider":
        first["provider_name"] = "registry.example/untrusted/openstack"
    elif mutation == "import":
        first["change"]["importing"] = {"id": str(uuid4())}
    elif mutation in {"moved", "deposed"}:
        first["previous_address" if mutation == "moved" else "deposed"] = "other"
    elif mutation in {"deferred", "drift"}:
        plan["deferred_changes" if mutation == "deferred" else "resource_drift"] = [first]
    elif mutation == "incomplete":
        plan["complete"] = False
    elif mutation == "errored":
        plan["errored"] = True
    elif mutation == "provisioner":
        plan["configuration"]["root_module"]["provisioners"] = [{"type": "local-exec"}]
    elif mutation == "unknown_metadata":
        first["change"]["after_unknown"]["metadata"] = True
    elif mutation == "changed_field":
        first["change"]["after"]["name"] = "other"
    elif mutation == "new_format":
        plan["format_version"] = "2.0"
    else:
        port = expected["openstack_networking_port_v2.quarantine"]["expected"]
        if mutation == "wrong_project":
            port["tenant_id"] = str(uuid4())
        elif mutation == "active_port":
            port["admin_state_up"] = True
        elif mutation == "unsecured_port":
            port["port_security_enabled"] = False
        elif mutation == "missing_security_group":
            port["security_group_ids"] = []
        else:
            expected["openstack_compute_instance_v2.application"]["expected"]["metadata"] = {}
        plan = plan_for(expected)
    with pytest.raises(NativeHeld):
        validate_plan(plan, expected, binding)


class Journal:
    def __init__(self) -> None:
        self.claimed = False
        self.events: list[tuple[str, dict[str, Any]]] = []

    def claim(self, binding: NativeBinding) -> bool:
        if self.claimed:
            return False
        self.claimed = True
        return True

    def record(self, binding: NativeBinding, event: str, facts: dict[str, Any]) -> None:
        self.events.append((event, facts))


class Authority:
    def __init__(self, denied: str = "") -> None:
        self.denied = denied
        self.calls: list[str] = []

    def require_current(self, binding: NativeBinding, boundary: str) -> None:
        self.calls.append(boundary)
        if boundary == self.denied:
            raise NativeHeld("revoked")


class Tool:
    def __init__(self, journal: Journal, result: ProcessResult | None = None) -> None:
        self.journal, self.result = journal, result or ProcessResult(0, False)
        self.applies = 0

    def inspect(self, binding: NativeBinding) -> dict[str, Any]:
        return {"bundle_sha256": binding.bundle_sha256}

    def apply(self, binding: NativeBinding, heartbeat: Callable[[], None]) -> ProcessResult:
        assert self.journal.claimed
        assert self.journal.events[-1][0] == "apply_started"
        heartbeat()
        self.applies += 1
        return self.result

    def state(self, binding: NativeBinding) -> dict[str, Any]:
        return {"resources": []}


class Observer:
    def __init__(self, outcome: str = "observed_present") -> None:
        self.outcome = outcome

    def observe(self, binding: NativeBinding, state: dict[str, Any]) -> dict[str, Any]:
        return {
            "binding_sha256": binding.fingerprint,
            "independent": True,
            "outcome": self.outcome,
            "observed_at": 100,
        }


def test_committed_attempt_precedes_apply_and_never_repeats(binding: NativeBinding) -> None:
    journal, authority = Journal(), Authority()
    tool = Tool(journal)
    execution = SavedPlanExecution(authority, journal, tool, Observer(), lambda: 100)
    result = execution.execute(binding)
    assert result["observation"]["outcome"] == "observed_present"
    assert not result["application_ready"] and not result["activation_authorized"]
    with pytest.raises(NativeHeld, match="requires_reconciliation"):
        execution.execute(binding)
    assert tool.applies == 1
    assert "before_saved_plan_apply" in authority.calls
    assert "during_saved_plan_apply" in authority.calls


@pytest.mark.parametrize(
    "boundary", ["preflight", "before_saved_plan_apply", "during_saved_plan_apply"]
)
def test_revocation_prevents_effect(binding: NativeBinding, boundary: str) -> None:
    journal = Journal()
    tool = Tool(journal)
    execution = SavedPlanExecution(Authority(boundary), journal, tool, Observer(), lambda: 100)
    with pytest.raises(NativeHeld):
        execution.execute(binding)
    assert tool.applies == 0


@pytest.mark.parametrize("process", [ProcessResult(1, False), ProcessResult(-9, True)])
def test_failure_or_interruption_does_not_authorize_retry(
    binding: NativeBinding, process: ProcessResult
) -> None:
    journal = Journal()
    tool = Tool(journal, process)
    execution = SavedPlanExecution(Authority(), journal, tool, Observer("held"), lambda: 100)
    result = execution.execute(binding)
    assert result["observation"]["outcome"] == "held" and not result["retry_authorized"]
    with pytest.raises(NativeHeld):
        execution.execute(binding)
    assert tool.applies == 1


def test_expired_authority_never_claims(binding: NativeBinding) -> None:
    journal = Journal()
    with pytest.raises(NativeHeld):
        SavedPlanExecution(Authority(), journal, Tool(journal), Observer(), lambda: 200).execute(
            binding
        )
    assert not journal.claimed


def test_real_subprocess_revocation_kills_child_without_exposing_output(tmp_path: Path) -> None:
    calls = 0

    def heartbeat() -> None:
        nonlocal calls
        calls += 1
        if calls > 2:
            raise NativeHeld("revoked")

    result, _ = run(
        [sys.executable, "-c", "import time; time.sleep(5)"], tmp_path, {}, 10, heartbeat
    )
    assert result.interrupted and result.exit_code != 0


def test_real_subprocess_output_is_bounded(tmp_path: Path) -> None:
    result, output = run(
        [sys.executable, "-c", "print('sensitive' * 1000)"], tmp_path, {}, 2, lambda: None, 100
    )
    assert result.interrupted and output == b""


def test_protected_input_rejects_symlink_fifo_and_world_writable(tmp_path: Path) -> None:
    file = tmp_path / "input"
    file.write_text("{}")
    link = tmp_path / "link"
    link.symlink_to(file)
    with pytest.raises(NativeHeld):
        protected_read(link, 10)
    file.chmod(0o666)
    with pytest.raises(NativeHeld):
        protected_read(file, 10)
    fifo = tmp_path / "fifo"
    os.mkfifo(fifo)
    with pytest.raises(NativeHeld):
        protected_read(fifo, 10)


class NativeFixture:
    def __init__(self, binding: NativeBinding) -> None:
        self.expected = resources(binding)
        self.user = uuid4().hex
        self.calls: list[str] = []
        self.documents: dict[str, dict[str, Any]] = {
            "/auth/tokens": {
                "token": {
                    "user": {"id": self.user},
                    "project": {"id": binding.project_id},
                    "expires_at": "2100-01-01T00:00:00Z",
                }
            }
        }
        self.state: dict[str, Any] = {"resources": []}
        ids = {contract["kind"]: str(uuid4()) for contract in self.expected.values()}
        for address, contract in self.expected.items():
            kind = contract["kind"]
            attrs = copy.deepcopy(contract["expected"]) | {"id": ids[kind]}
            if kind == "server":
                attrs["block_device"] = [
                    {"uuid": ids["volume"], "source_type": "volume", "destination_type": "volume"}
                ]
                attrs["network"] = [{"port": ids["port"]}]
            resource_type, name = address.split(".")
            self.state["resources"].append(
                {
                    "mode": "managed",
                    "type": resource_type,
                    "name": name,
                    "provider": (
                        'provider["registry.terraform.io/terraform-provider-openstack/openstack"]'
                    ),
                    "instances": [{"attributes": attrs}],
                }
            )
            native = copy.deepcopy(attrs) | {"project_id": binding.project_id}
            if kind == "server":
                native.update(status="ACTIVE", flavor={"id": attrs["flavor_id"]})
                native["os-extended-volumes:volumes_attached"] = [{"id": ids["volume"]}]
            elif kind == "port":
                native.update(
                    fixed_ips=attrs["fixed_ip"],
                    security_groups=attrs["security_group_ids"],
                    device_id=ids["server"],
                )
            else:
                native.update(status="in-use")
            self.documents[f"/{kind}s/{ids[kind]}"] = {kind: native}

    def get(self, service: str, path: str, *, subject: bool = False) -> dict[str, Any]:
        self.calls.append(path)
        if path not in self.documents:
            raise NativeHeld("native_read_not_observed")
        return self.documents[path]

    def observer(self) -> OpenStackReadback:
        return OpenStackReadback(self, self.expected, self.user, uuid4().hex, lambda: 100)


def test_exact_native_readback_and_no_application_readiness(binding: NativeBinding) -> None:
    fixture = NativeFixture(binding)
    result = fixture.observer().observe(binding, fixture.state)
    assert result["outcome"] == "observed_present" and len(result["objects"]) == 3
    assert not result["application_ready"] and not result["activation_authorized"]
    assert fixture.calls[0] == "/auth/tokens"
    assert all("?" not in path for path in fixture.calls)


@pytest.mark.parametrize(
    "mutation", ["wrong_project", "wrong_user", "expired_token", "writer_is_observer"]
)
def test_observer_identity_is_bound(binding: NativeBinding, mutation: str) -> None:
    fixture = NativeFixture(binding)
    token = fixture.documents["/auth/tokens"]["token"]
    if mutation == "wrong_project":
        token["project"]["id"] = str(uuid4())
    elif mutation == "wrong_user":
        token["user"]["id"] = uuid4().hex
    elif mutation == "expired_token":
        token["expires_at"] = "1970-01-01T00:00:01Z"
    with pytest.raises(NativeHeld):
        if mutation == "writer_is_observer":
            OpenStackReadback(fixture, fixture.expected, fixture.user, fixture.user, lambda: 100)
        else:
            fixture.observer().observe(binding, fixture.state)
    assert not any(path.startswith("/servers/") for path in fixture.calls)


@pytest.mark.parametrize(
    "mutation",
    [
        "404",
        "unknown_id",
        "foreign_project",
        "metadata",
        "active_port",
        "wrong_ip",
        "wrong_attachment",
        "wrong_volume",
        "tainted",
        "unowned",
        "duplicate",
    ],
)
def test_readback_uncertainty_and_drift_stay_held(binding: NativeBinding, mutation: str) -> None:
    fixture = NativeFixture(binding)
    server_path = next(k for k in fixture.documents if k.startswith("/servers/"))
    server = fixture.documents[server_path]["server"]
    port = next(v["port"] for v in fixture.documents.values() if "port" in v)
    if mutation == "404":
        del fixture.documents[server_path]
    elif mutation == "unknown_id":
        fixture.state["resources"] = []
    elif mutation == "foreign_project":
        server["project_id"] = str(uuid4())
    elif mutation == "metadata":
        server["metadata"] = {}
    elif mutation == "active_port":
        port["admin_state_up"] = True
    elif mutation == "wrong_ip":
        port["fixed_ips"] = [{"subnet_id": str(uuid4()), "ip_address": "192.0.2.99"}]
    elif mutation == "wrong_attachment":
        port["device_id"] = str(uuid4())
    elif mutation == "wrong_volume":
        server["os-extended-volumes:volumes_attached"] = [{"id": str(uuid4())}]
    else:
        if mutation == "tainted":
            fixture.state["resources"][0]["instances"][0]["status"] = "tainted"
        elif mutation == "unowned":
            fixture.state["resources"][0]["name"] += "_unowned"
        else:
            fixture.state["resources"].append(copy.deepcopy(fixture.state["resources"][0]))
        with pytest.raises(NativeHeld):
            fixture.observer().observe(binding, fixture.state)
        return
    result = fixture.observer().observe(binding, fixture.state)
    assert result["outcome"] == "held" and not result["retry_authorized"]


def test_state_for_each_and_module_addresses(binding: NativeBinding) -> None:
    fixture = NativeFixture(binding)
    resource = fixture.state["resources"][0]
    resource["module"] = "module.application"
    resource["instances"][0]["index_key"] = "one"
    objects = state_objects(fixture.state)
    assert 'module.application.openstack_compute_instance_v2.application["one"]' in objects


def test_bundle_checks_all_bytes_and_rejects_unlisted_plugins(tmp_path: Path) -> None:
    for name in ("plan.bin", ".terraform.lock.hcl"):
        (tmp_path / name).write_bytes(b"synthetic")
    manifest: dict[str, Any] = {
        "schema_version": 1,
        "terraform_version": "1.16.0",
        "terraform_sha256": "a" * 64,
        "saved_plan": "plan.bin",
        "plan_json_sha256": "b" * 64,
        "environment_sha256": "c" * 64,
        "resources": {},
        "files": {
            name: hashlib.sha256(b"synthetic").hexdigest()
            for name in ("plan.bin", ".terraform.lock.hcl")
        },
    }
    (tmp_path / "bundle.json").write_text(json.dumps(manifest))
    assert verify_bundle(tmp_path, digest(manifest)) == manifest
    (tmp_path / "unlisted.auto.tfvars").write_text("dangerous=1")
    with pytest.raises(NativeHeld, match="unlisted"):
        verify_bundle(tmp_path, digest(manifest))
    (tmp_path / "unlisted.auto.tfvars").unlink()
    (tmp_path / "plan.bin").write_bytes(b"changed")
    with pytest.raises(NativeHeld, match="artifact_changed"):
        verify_bundle(tmp_path, digest(manifest))


def test_terraform_never_inherits_unsafe_environment(
    binding: NativeBinding, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("TF_CLI_ARGS_apply", "-lock=false")
    credentials = {}
    for name in ("OS_APPLICATION_CREDENTIAL_ID", "OS_APPLICATION_CREDENTIAL_SECRET"):
        file = tmp_path / name
        file.write_text("synthetic-protected-credential")
        credentials[name] = file
    environment = {
        "OS_PROJECT_ID": binding.project_id,
        "OS_AUTH_TYPE": "v3applicationcredential",
        "OS_AUTH_URL": "https://identity.invalid/v3",
        "OS_CACERT": "/trusted/ca.pem",
    }
    tool = TerraformSavedPlan(tmp_path / "terraform", tmp_path, environment, credentials)
    assert "TF_CLI_ARGS_apply" not in tool.environment(binding)
    environment["OS_INSECURE"] = "true"
    with pytest.raises(NativeHeld):
        tool.environment(binding)


def test_saved_plan_adapter_runs_exact_command_and_rejects_changed_state(
    binding: NativeBinding,
    tmp_path: Path,
) -> None:
    root = tmp_path / "bundle"
    (root / ".terraform").mkdir(parents=True)
    expected = resources(binding)
    plan = plan_for(expected)
    state = {
        "version": 4,
        "lineage": binding.state_lineage,
        "serial": binding.state_serial,
        "resources": [],
    }
    marker, arguments = tmp_path / "accepted", tmp_path / "arguments.json"
    executable = tmp_path / "fixture-terraform"
    executable.write_text(
        f"#!{sys.executable}\nimport json,sys\nfrom pathlib import Path\n"
        f"state={state!r}\nplan={plan!r}\nmarker=Path({str(marker)!r})\n"
        "command=sys.argv[1:]\n"
        "if command==['version','-json']: print(json.dumps({'terraform_version':'1.16.0'}))\n"
        "elif command==['workspace','show']: print('default')\n"
        "elif command==['state','pull']:\n"
        " state['serial'] += int(marker.exists()); print(json.dumps(state))\n"
        "elif command[:2]==['show','-json']: print(json.dumps(plan))\n"
        "elif command[0]=='apply':\n"
        f" Path({str(arguments)!r}).write_text(json.dumps(command))\n"
        " marker.write_text('accepted')\n"
        "else: sys.exit(2)\n"
    )
    executable.chmod(0o700)
    (root / "plan.bin").write_bytes(b"synthetic-opaque-plan")
    (root / ".terraform.lock.hcl").write_text("synthetic-provider-lock")
    (root / ".terraform/terraform.tfstate").write_text(
        json.dumps(
            {
                "backend": {
                    "type": "http",
                    "config": {
                        "address": "https://state.invalid/value",
                        "lock_address": "https://state.invalid/lock",
                        "unlock_address": "https://state.invalid/lock",
                        "skip_cert_verification": False,
                    },
                }
            }
        )
    )
    credentials = {}
    for name in ("OS_APPLICATION_CREDENTIAL_ID", "OS_APPLICATION_CREDENTIAL_SECRET"):
        file = tmp_path / name
        file.write_text("synthetic-protected-credential")
        credentials[name] = file
    environment = {
        "OS_PROJECT_ID": binding.project_id,
        "OS_AUTH_TYPE": "v3applicationcredential",
        "OS_AUTH_URL": "https://identity.invalid/v3",
        "OS_CACERT": "/trusted/ca.pem",
    }
    manifest = {
        "schema_version": 1,
        "terraform_version": "1.16.0",
        "terraform_sha256": hashlib.sha256(executable.read_bytes()).hexdigest(),
        "saved_plan": "plan.bin",
        "plan_json_sha256": digest(plan),
        "environment_sha256": digest(environment),
        "resources": expected,
        "files": {
            p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in root.rglob("*")
            if p.is_file()
        },
    }
    (root / "bundle.json").write_text(json.dumps(manifest))
    bound = replace(binding, bundle_sha256=digest(manifest))
    tool = TerraformSavedPlan(executable, root, environment, credentials)
    assert tool.inspect(bound)["resource_count"] == 3
    assert tool.apply(bound, lambda: None) == ProcessResult(0, False)
    command = json.loads(arguments.read_text())
    assert command == [
        "apply",
        "-input=false",
        "-no-color",
        "-lock=true",
        "-lock-timeout=0s",
        "-parallelism=1",
        str(root / "plan.bin"),
    ]
    assert tool.state(bound)["serial"] == binding.state_serial + 1
    with pytest.raises(NativeHeld, match="state_changed"):
        tool.inspect(bound)
