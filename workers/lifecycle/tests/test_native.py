"""Native execution boundaries against synthetic owner and API responses."""

import copy
import json
import os
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest

from lifecycle_worker.application.api_plan import validate_api_plan
from lifecycle_worker.application.native import (
    NativeApiExecution,
    NativeBinding,
    NativeHeld,
    decode,
    digest,
)
from lifecycle_worker.infrastructure.native_files import protected_read
from lifecycle_worker.infrastructure.openstack_api import OpenStackApi
from lifecycle_worker.infrastructure.openstack_readback import OpenStackReadback


@pytest.fixture
def binding() -> NativeBinding:
    values: dict[str, Any] = {
        key: str(uuid4())
        for key in (
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
            "custody_id",
        )
    }
    return NativeBinding.parse(
        values
        | {
            "plan_digest": "a" * 64,
            "operation_plan_sha256": "b" * 64,
            "ownership_digest": "c" * 64,
            "custody_generation": 1,
            "expires_at": 200,
        }
    )


def plan_for(binding: NativeBinding) -> dict[str, Any]:
    return {
        "schema_version": 1,
        **{
            key: binding.document()[key]
            for key in ("project_id", "custody_id", "custody_generation", "ownership_digest")
        },
        "api_versions": {"compute": "2.1", "network": "2.0", "volume": "3.0"},
        "resources": [
            {
                "key": "nic",
                "kind": "port",
                "spec": {
                    "name": "nic",
                    "network_id": str(uuid4()),
                    "fixed_ips": [{"subnet_id": str(uuid4()), "ip_address": "192.0.2.8"}],
                    "security_groups": [str(uuid4())],
                    "admin_state_up": False,
                    "port_security_enabled": True,
                },
            },
            {
                "key": "boot",
                "kind": "volume",
                "spec": {
                    "name": "boot",
                    "size": 10,
                    "volume_type": "encrypted",
                    "availability_zone": "nova",
                    "imageRef": str(uuid4()),
                },
            },
            {
                "key": "vm",
                "kind": "server",
                "spec": {
                    "name": "vm",
                    "flavorRef": "small",
                    "availability_zone": "nova",
                    "config_drive": True,
                    "ports": ["nic"],
                    "volumes": [{"key": "boot", "boot_index": 0}],
                },
            },
        ],
    }


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
        assert self.claimed
        self.events.append((event, facts))

    def resources(self, binding: NativeBinding) -> dict[str, dict[str, str]]:
        return {
            facts["resource_key"]: {"kind": facts["kind"], "id": facts["native_id"]}
            for event, facts in self.events
            if event == "request_accepted"
        }

    def transfers(self, binding: NativeBinding) -> dict[str, dict[str, Any]]:
        return {
            facts["resource_key"]: facts
            for event, facts in self.events
            if event == "disk_transferred"
        }


class Authority:
    def __init__(self, denied: str = "") -> None:
        self.denied = denied
        self.calls: list[str] = []

    def require_current(self, binding: NativeBinding, boundary: str) -> None:
        self.calls.append(boundary)
        if self.denied == boundary:
            raise NativeHeld("revoked")


class Tool:
    def __init__(self, journal: Journal) -> None:
        self.journal = journal
        self.calls = 0

    def inspect(self, binding: NativeBinding) -> dict[str, Any]:
        return {"native_write_authorized": False}

    def execute(self, binding: NativeBinding, boundary: Callable[[], None]) -> None:
        assert self.journal.claimed
        boundary()
        self.calls += 1


class Observer:
    def observe(self, binding: NativeBinding, objects: dict[str, Any]) -> dict[str, Any]:
        return {
            "binding_sha256": binding.fingerprint,
            "independent": True,
            "observed_at": 100,
            "outcome": "observed_present",
        }


@pytest.mark.parametrize("raw", [b'{"a":1,"a":2}', b'{"a":NaN}', b"[]", b"{} " * 10])
def test_strict_native_documents(raw: bytes) -> None:
    with pytest.raises(NativeHeld):
        decode(raw, 20)


@pytest.mark.parametrize(
    "field,value",
    [
        ("expires_at", True),
        ("custody_generation", True),
        ("ownership_digest", "default"),
        ("operation_plan_sha256", "missing"),
        ("project_id", "arbitrary"),
    ],
)
def test_invalid_binding(binding: NativeBinding, field: str, value: Any) -> None:
    with pytest.raises(NativeHeld):
        NativeBinding.parse(binding.document() | {field: value})


@pytest.mark.parametrize(
    "fault",
    [
        "changed",
        "extra",
        "active_port",
        "no_security",
        "free_device",
        "shared_port",
        "bootless",
        "unknown_kind",
        "api_version",
    ],
)
def test_native_operation_schema_denies_unsafe_intent(binding: NativeBinding, fault: str) -> None:
    plan = plan_for(binding)
    bound = replace(binding, operation_plan_sha256=digest(plan))
    if fault == "changed":
        plan["resources"][0]["spec"]["name"] = "changed"
    elif fault == "extra":
        plan["command"] = "unapproved"
    elif fault == "active_port":
        plan["resources"][0]["spec"]["admin_state_up"] = True
    elif fault == "no_security":
        plan["resources"][0]["spec"]["security_groups"] = []
    elif fault == "free_device":
        plan["resources"][2]["spec"]["ports"] = []
    elif fault == "shared_port":
        plan["resources"][2]["spec"]["ports"] *= 2
    elif fault == "bootless":
        plan["resources"][2]["spec"]["volumes"][0]["boot_index"] = -1
    elif fault == "unknown_kind":
        plan["resources"][0]["kind"] = "shell"
    else:
        plan["api_versions"]["compute"] = "latest"
    if fault != "changed":
        bound = replace(bound, operation_plan_sha256=digest(plan))
    with pytest.raises(NativeHeld):
        validate_api_plan(plan, bound)


class NativeFixture:
    def __init__(self, binding: NativeBinding, plan: dict[str, Any]) -> None:
        self.binding, self.plan = binding, plan
        self.writer, self.reader = str(uuid4()), str(uuid4())
        self.objects: dict[str, dict[str, str]] = {}
        self.documents: dict[str, dict[str, Any]] = {}
        self.posts: list[str] = []
        self.fail = ""

    def create(
        self,
        binding: NativeBinding,
        service: str,
        path: str,
        body: dict[str, Any],
        boundary: Callable[[], None],
    ) -> dict[str, Any]:
        boundary()
        kind = next(iter(body))
        spec = body[kind]
        key = next(
            row["key"] for row in self.plan["resources"] if row["spec"]["name"] == spec["name"]
        )
        object_id = str(uuid4())
        self.posts.append(kind)
        self.objects[key] = {"kind": kind, "id": object_id}
        native = copy.deepcopy(spec) | {"id": object_id, "tenant_id": binding.project_id}
        if kind == "server":
            native.update(
                status="ACTIVE",
                flavor={"id": spec["flavorRef"]},
                **{
                    "OS-EXT-AZ:availability_zone": spec["availability_zone"],
                    "os-extended-volumes:volumes_attached": [{"id": self.objects["boot"]["id"]}],
                },
            )
            self.documents[self.objects["boot"]["id"]]["volume"].update(
                status="in-use", attachments=[{"server_id": object_id}]
            )
            self.documents[self.objects["nic"]["id"]]["port"]["device_id"] = object_id
        elif kind == "volume":
            native.update(status="available", volume_image_metadata={"image_id": spec["imageRef"]})
        self.documents[object_id] = {kind: native}
        if self.fail == kind:
            raise OSError("accepted reply lost")
        return {"document": {kind: {"id": object_id}}, "request_id": "req-" + str(uuid4())}

    def get(self, service: str, path: str, *, subject: bool = False) -> dict[str, Any]:
        if subject:
            return {
                "token": {
                    "user": {"id": self.reader},
                    "project": {"id": self.binding.project_id},
                    "expires_at": "2099-01-01T00:00:00Z",
                }
            }
        if path.endswith("/os-interface"):
            return {"interfaceAttachments": [{"port_id": self.objects["nic"]["id"]}]}
        return self.documents[path.rsplit("/", 1)[-1]]

    def observer(self) -> OpenStackReadback:
        return OpenStackReadback(
            self,
            {r["key"]: r for r in self.plan["resources"]},
            self.reader,
            self.writer,
            lambda: 100,
        )


def campaign(
    binding: NativeBinding, tmp_path: Path
) -> tuple[NativeBinding, NativeApiExecution, Journal, NativeFixture]:
    plan = plan_for(binding)
    bound = replace(binding, operation_plan_sha256=digest(plan))
    path = tmp_path / "plan.json"
    path.write_text(json.dumps(plan))
    journal = Journal()
    native = NativeFixture(bound, plan)
    adapter = OpenStackApi(path, native, journal, interval=0)
    return (
        bound,
        NativeApiExecution(Authority(), journal, adapter, native.observer(), lambda: 100),
        journal,
        native,
    )


def test_native_create_order_journal_and_independent_readback(
    binding: NativeBinding, tmp_path: Path
) -> None:
    bound, execution, journal, native = campaign(binding, tmp_path)
    result = execution.execute(bound)
    assert native.posts == ["port", "volume", "server"]
    assert result["observation"]["outcome"] == "observed_present"
    assert not result["application_ready"] and not result["activation_authorized"]
    assert [event for event, _ in journal.events].count("request_started") == 3
    with pytest.raises(NativeHeld, match="reconciliation"):
        execution.execute(bound)
    assert len(native.posts) == 3


@pytest.mark.parametrize("lost", ["port", "volume", "server"])
def test_native_accepted_reply_loss_never_repeats(
    binding: NativeBinding, tmp_path: Path, lost: str
) -> None:
    bound, execution, journal, native = campaign(binding, tmp_path)
    native.fail = lost
    with pytest.raises(NativeHeld):
        execution.execute(bound)
    count = len(native.posts)
    assert journal.events[-1][0] == "outcome_unknown"
    assert execution.reconcile(bound)["outcome"] == "held"
    with pytest.raises(NativeHeld):
        execution.execute(bound)
    assert len(native.posts) == count


@pytest.mark.parametrize("boundary", ["preflight", "before_api_sequence", "during_api_sequence"])
def test_revocation_prevents_effect(binding: NativeBinding, boundary: str) -> None:
    journal = Journal()
    tool = Tool(journal)
    with pytest.raises(NativeHeld):
        NativeApiExecution(Authority(boundary), journal, tool, Observer(), lambda: 100).execute(
            binding
        )
    assert tool.calls == 0


@pytest.mark.parametrize(
    "kind,field,value",
    [
        ("server", "status", "ERROR"),
        ("server", "config_drive", 1),
        ("port", "admin_state_up", True),
        ("port", "security_groups", []),
        ("volume", "size", True),
        ("volume", "attachments", []),
    ],
)
def test_native_readback_drift_holds(
    binding: NativeBinding, tmp_path: Path, kind: str, field: str, value: Any
) -> None:
    bound, execution, journal, native = campaign(binding, tmp_path)
    execution.execute(bound)
    for document in native.documents.values():
        if kind in document:
            document[kind][field] = value
    assert execution.reconcile(bound)["outcome"] == "held"


def test_protected_input_rejects_symlink_fifo_and_world_writable(tmp_path: Path) -> None:
    regular = tmp_path / "regular"
    regular.write_text("protected")
    assert protected_read(regular, 100) == b"protected"
    link = tmp_path / "link"
    link.symlink_to(regular)
    fifo = tmp_path / "fifo"
    os.mkfifo(fifo)
    for path in (link, fifo):
        with pytest.raises(NativeHeld):
            protected_read(path, 100)
    regular.chmod(0o666)
    with pytest.raises(NativeHeld):
        protected_read(regular, 100)


class GrantClient:
    def __init__(self) -> None:
        self.calls: list[str] = []
        self.change: dict[str, Any] = {}
        self.fail: str | None = None

    def check(self, grant: dict[str, Any], boundary: str) -> dict[str, Any]:
        if boundary == self.fail:
            raise OSError("private dependency details")
        self.calls.append(boundary)
        return {
            "binding_sha256": digest(grant),
            "epoch": grant["epoch"],
            "boundary": boundary,
            "allowed": True,
            "authority_use": "native_boundary",
            "evaluated_at": 100,
            "expires_at": grant["expires_at"],
            **self.change,
        }


def stage_grant(binding: NativeBinding) -> dict[str, Any]:
    return {
        **{
            k: binding.document()[k]
            for k in ("job_id", "operation_id", "attempt_id", "epoch", "executor_id", "expires_at")
        },
        "grant_id": str(uuid4()),
        "stage": "provision",
        "plan_sha256": "c" * 64,
        "intent_digest": "d" * 64,
        "native_binding": binding.document(),
    }


def test_native_plan_uses_live_stage_authority(binding: NativeBinding) -> None:
    from lifecycle_worker.application.native_authority import GrantedNativeAuthority

    client = GrantClient()
    authority = GrantedNativeAuthority(stage_grant(binding), client, lambda: 100)
    journal = Journal()
    tool = Tool(journal)
    result = NativeApiExecution(authority, journal, tool, Observer(), lambda: 100).execute(binding)
    assert client.calls == ["preflight", "before_api_sequence", "during_api_sequence"]
    assert tool.calls == 1 and result["activation_authorized"] is False
    with pytest.raises(NativeHeld):
        authority.require_current(replace(binding, project_id=str(uuid4())), "preflight")


@pytest.mark.parametrize(
    "change",
    [
        {"allowed": 1},
        {"authority_use": "simulation_boundary"},
        {"boundary": "preflight"},
        {"evaluated_at": True},
        {"evaluated_at": 94},
        {"evaluated_at": 101},
        {"expires_at": 201},
        {"epoch": str(uuid4())},
        {"binding_sha256": "0" * 64},
    ],
)
def test_native_stage_authority_rejects_rebinding_or_stale_reply(
    binding: NativeBinding, change: dict[str, Any]
) -> None:
    from lifecycle_worker.application.native_authority import GrantedNativeAuthority

    client = GrantClient()
    client.change = change
    authority = GrantedNativeAuthority(stage_grant(binding), client, lambda: 100)
    with pytest.raises(NativeHeld):
        authority.require_current(binding, "before_api_sequence")


@pytest.mark.parametrize(
    "field", ["job_id", "operation_id", "attempt_id", "epoch", "executor_id", "expires_at"]
)
def test_native_plan_and_grant_fields_must_agree(binding: NativeBinding, field: str) -> None:
    from lifecycle_worker.application.native_authority import GrantedNativeAuthority

    grant = stage_grant(binding)
    grant[field] = 201 if field == "expires_at" else str(uuid4())
    with pytest.raises(NativeHeld):
        GrantedNativeAuthority(grant, GrantClient(), lambda: 100)


def test_lost_native_redemption_response_never_launches_or_retries(binding: NativeBinding) -> None:
    from lifecycle_worker.application.native_authority import GrantedNativeAuthority

    client = GrantClient()
    client.fail = "before_api_sequence"
    journal = Journal()
    tool = Tool(journal)
    authority = GrantedNativeAuthority(stage_grant(binding), client, lambda: 100)
    execution = NativeApiExecution(authority, journal, tool, Observer(), lambda: 100)
    with pytest.raises(NativeHeld, match="requires_reconciliation"):
        execution.execute(binding)
    client.fail = None
    with pytest.raises(NativeHeld, match="requires_reconciliation"):
        execution.execute(binding)
    assert tool.calls == 0 and journal.claimed
    assert journal.events[-1][0] == "outcome_unknown"


def test_published_native_grant_fixture_is_consumed_without_field_translation() -> None:
    from lifecycle_worker.application.native_authority import GrantedNativeAuthority

    fixture = json.loads(
        (Path(__file__).parent / "fixtures/native-stage-grant-v1.json").read_text()
    )
    authority = GrantedNativeAuthority(fixture["grant"], GrantClient(), lambda: 100)
    authority.require_current(authority.binding, fixture["boundary"])
