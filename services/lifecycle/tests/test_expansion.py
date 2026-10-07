"""Real PostgreSQL ownership collisions, transfer holds and shared enterprise budgets."""

from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from typing import Any
from uuid import uuid4

import pytest

from lifecycle.application.adoption import Adoptions
from lifecycle.application.enterprise import Enterprise
from lifecycle.domain.admission import digest
from lifecycle.domain.execution import Rejected
from lifecycle.domain.expansion import operation


def uid() -> str:
    return str(uuid4())


def scope() -> dict[str, Any]:
    return {
        "site_id": uid(),
        "environment": uid(),
        "resource_id": uid(),
        "endpoint_id": uid(),
        "native_scope": "datacenter-4",
        "object_id": "vm-21",
        "platform": "vmware",
        "tuple_sha256": "a" * 64,
    }


class AdoptionOwner:
    def __init__(self) -> None:
        self.writer, self.observer, self.old, self.epoch = uid(), uid(), uid(), uid()
        self.values = {"cpu.count": "c" * 64}
        self.fenced: list[str] = []
        self.transfer: str | None = None
        self.active: list[str] = []
        self.now = 100

    def observe(
        self, tenant: str, native_scope: dict[str, Any], selected: list[str]
    ) -> dict[str, Any]:
        return {
            "tenant_id": tenant,
            "scope": native_scope,
            "fields": dict(self.values),
            "observer_id": self.observer,
            "writer_id": self.writer,
            "observed_at": self.now,
            "expires_at": 200,
            "epoch": self.epoch,
            "ownership_revision": 1,
            "old_writers": {f: [self.old] for f in selected},
            "fenced_writers": self.fenced,
            "transfer_to": self.transfer,
            "active_effects": self.active,
            "certain": True,
            "grant_sha256": "f" * 64,
        }


def imported(database: Any) -> tuple[Adoptions, AdoptionOwner, str, str, str]:
    owner = AdoptionOwner()
    app = Adoptions(database, owner, lambda: 100)
    tenant, actor = uid(), uid()
    row = app.create(tenant, actor, uid(), scope(), ["cpu.count"])
    adopted = str(row["id"])
    app.command(tenant, adopted, actor, uid(), 1, "import", owner.values)
    return app, owner, tenant, actor, adopted


def test_import_never_grants_write_authority_and_transfer_is_separate(database: Any) -> None:
    app, owner, tenant, actor, adopted = imported(database)
    with pytest.raises(Rejected, match="write_authority_absent"):
        app.require_managed(tenant, adopted, ["cpu.count"])
    with pytest.raises(Rejected, match="old_writer_transfer"):
        app.command(tenant, adopted, actor, uid(), 2, "transfer")
    assert app.read(tenant, adopted)["state"] == "held"
    app.command(tenant, adopted, actor, uid(), 3, "reconcile")
    owner.fenced, owner.transfer = [owner.old], owner.writer
    result = app.command(tenant, adopted, actor, uid(), 4, "transfer")
    assert result["state"] == "managed"
    assert app.require_managed(tenant, adopted, ["cpu.count"])["writer_id"] == owner.writer
    owner.values["cpu.count"] = "e" * 64
    with pytest.raises(Rejected, match="drift_changed"):
        app.require_managed(tenant, adopted, ["cpu.count"])
    assert app.read(tenant, adopted)["state"] == "held"


def test_field_collision_crosses_tenants_and_detach_never_deletes_vm(database: Any) -> None:
    app, owner, tenant, actor, adopted = imported(database)
    same = app.read(tenant, adopted)["scope"]
    foreign = uid()
    other = str(app.create(foreign, actor, uid(), same, ["cpu.count"])["id"])
    with pytest.raises(Rejected, match="collision"):
        app.command(foreign, other, actor, uid(), 1, "import", owner.values)
    owner.fenced, owner.transfer = [owner.writer], owner.old
    assert app.command(tenant, adopted, actor, uid(), 2, "detach")["state"] == "detached"
    assert app.read(tenant, adopted)["baseline"]["fields"] == owner.values
    app.command(foreign, other, actor, uid(), 2, "reconcile")
    assert (
        app.command(foreign, other, actor, uid(), 3, "import", owner.values)["state"] == "imported"
    )


def test_import_drift_and_wrong_tenant_are_denied(database: Any) -> None:
    app, owner, tenant, actor, adopted = imported(database)
    with pytest.raises(Rejected, match="not_found"):
        app.read(uid(), adopted)
    owner.observer = owner.writer
    with pytest.raises(Rejected, match="independent"):
        app.command(tenant, adopted, actor, uid(), 2, "transfer")


def spec(tenant: str | None = None, endpoint: str | None = None) -> dict[str, Any]:
    t, native = tenant or uid(), scope()
    if endpoint:
        native["endpoint_id"] = endpoint
    return {
        "id": uid(),
        "tenant_id": t,
        "scope": native,
        "operation": "ha_failover",
        "plan_sha256": "a" * 64,
        "adapter_sha256": "b" * 64,
        "impact_pool": digest({"impact": native["site_id"]}),
        "prerequisites": {
            k: digest(k)
            for k in ("safety", "policy", "services", "recovery", "ownership", "capacity")
        },
        "demands": {
            digest({"tenant": t}): 1,
            digest({"endpoint": native["endpoint_id"]}): 1,
            digest({"impact": native["site_id"]}): 1,
        },
        "depends_on": [],
        "windows": [{"start": 90, "end": 200}],
        "blackouts": [],
        "priority": 50,
        "not_before": 90,
        "deadline": 200,
        "maximum_seconds": 20,
    }


class EnterpriseOwner:
    now = 100
    deny = False
    outcome = "succeeded"
    fenced = True
    policy = True

    def require_current(self, specification: dict[str, Any], boundary: str) -> None:
        if self.deny:
            raise Rejected("owner_revoked", 423)

    def budgets(self, pools: list[str]) -> dict[str, Any]:
        return {
            p: {
                "limit": 1,
                "external_usage": 0,
                "observed_at": self.now,
                "expires_at": self.now + 30,
                "evidence_sha256": "d" * 64,
            }
            for p in pools
        }

    def observe(self, specification: dict[str, Any], lease: str) -> dict[str, Any]:
        return {
            "operation_id": specification["id"],
            "lease": lease,
            "specification_sha256": digest(specification),
            "observer_id": uid(),
            "executor_id": uid(),
            "observed_at": self.now,
            "outcome": self.outcome,
            "writer_fenced": self.fenced,
            "policy_sha256": specification["prerequisites"]["policy"] if self.policy else "0" * 64,
            "services_sha256": specification["prerequisites"]["services"],
            "recovery_sha256": specification["prerequisites"]["recovery"],
            "evidence_sha256": "d" * 64,
        }


def test_shared_endpoint_unknown_budget_and_stop_boundary(database: Any) -> None:
    owner = EnterpriseOwner()
    app = Enterprise(database, owner, lambda: owner.now)
    first = spec()
    second = spec(endpoint=first["scope"]["endpoint_id"])
    w = app.create(first["tenant_id"], uid(), uid(), [first])
    app.create(second["tenant_id"], uid(), uid(), [second])
    claim = app.claim()
    assert claim is not None
    assert app.claim() is None
    tenant, op, lease = claim["tenant_id"], claim["operation_id"], claim["lease"]
    app.boundary(tenant, op, lease)
    owner.now = 121
    assert app.claim() is None
    with pytest.raises(Rejected, match="boundary_held"):
        app.boundary(tenant, op, lease)
    owner.outcome = "unknown"
    assert app.reconcile(tenant, op, lease)["state"] == "unknown"
    assert app.claim() is None
    owner.outcome = "succeeded"
    owner.fenced = False
    with pytest.raises(Rejected, match="fenced"):
        app.reconcile(tenant, op, lease)
    owner.fenced, owner.policy = True, False
    with pytest.raises(Rejected, match="mandatory_outcome"):
        app.reconcile(tenant, op, lease)
    owner.policy = True
    app.reconcile(tenant, op, lease)
    assert app.claim() is not None
    if tenant == first["tenant_id"]:
        app.control(tenant, str(w["id"]), uid(), uid(), 1, "stop")


def test_dag_pause_stop_and_revocation(database: Any) -> None:
    owner = EnterpriseOwner()
    app = Enterprise(database, owner, lambda: owner.now)
    first = spec()
    second = spec(first["tenant_id"], first["scope"]["endpoint_id"])
    second["depends_on"] = [first["id"]]
    actor = uid()
    wave_id = str(app.create(first["tenant_id"], actor, uid(), [second, first])["id"])
    claim = app.claim()
    assert claim is not None and claim["operation_id"] == first["id"]
    app.control(first["tenant_id"], wave_id, actor, uid(), 1, "pause")
    with pytest.raises(Rejected, match="boundary_held"):
        app.boundary(first["tenant_id"], first["id"], claim["lease"])
    assert app.claim() is None
    app.control(first["tenant_id"], wave_id, actor, uid(), 2, "resume")
    owner.deny = True
    with pytest.raises(Rejected, match="owner_revoked"):
        app.boundary(first["tenant_id"], first["id"], claim["lease"])
    owner.deny = False
    app.control(first["tenant_id"], wave_id, actor, uid(), 3, "stop")
    app.reconcile(first["tenant_id"], first["id"], claim["lease"])
    assert app.claim() is None
    with pytest.raises(Rejected, match="stop_conflict"):
        app.control(first["tenant_id"], wave_id, actor, uid(), 4, "resume")


def test_mandatory_budgets_and_full_window() -> None:
    value = spec()
    changed = deepcopy(value)
    changed["demands"] = {"a" * 64: 1, "b" * 64: 1, "c" * 64: 1}
    with pytest.raises(Rejected, match="tenant_and_endpoint"):
        operation(changed)


def test_concurrent_dispatchers_share_correlated_impact_budget(database: Any) -> None:
    owner = EnterpriseOwner()
    app = Enterprise(database, owner, lambda: owner.now)
    first, second = spec(), spec()
    second["demands"].pop(second["impact_pool"])
    second["impact_pool"] = first["impact_pool"]
    second["demands"][second["impact_pool"]] = 1
    for item in (first, second):
        app.create(item["tenant_id"], uid(), uid(), [item])
    with ThreadPoolExecutor(max_workers=2) as pool:
        claims = list(pool.map(lambda _: app.claim(), range(2)))
    assert sum(c is not None for c in claims) == 1


def test_blackout_full_duration_and_failed_dependency_prevent_dispatch(database: Any) -> None:
    owner = EnterpriseOwner()
    app = Enterprise(database, owner, lambda: owner.now)
    first = spec()
    first["blackouts"] = [{"start": 110, "end": 130}]
    app.create(first["tenant_id"], uid(), uid(), [first])
    assert app.claim() is None
    owner.now = 130
    claim = app.claim()
    assert claim is not None
    owner.outcome = "failed"
    assert (
        app.reconcile(claim["tenant_id"], claim["operation_id"], claim["lease"])["state"]
        == "failed"
    )


def test_restart_after_lost_submission_does_not_resubmit(database: Any) -> None:
    from unittest.mock import MagicMock

    from lifecycle.application.enterprise_dispatch import EnterpriseDispatcher

    owner = EnterpriseOwner()
    app = Enterprise(database, owner, lambda: owner.now)
    item = spec()
    app.create(item["tenant_id"], uid(), uid(), [item])
    effects = MagicMock()
    effects.execute.side_effect = OSError("synthetic response loss")
    assert EnterpriseDispatcher(app, effects).tick() == {
        "operation_id": item["id"],
        "state": "reconciliation_required",
    }
    restarted = Enterprise(database, owner, lambda: owner.now)
    assert EnterpriseDispatcher(restarted, effects).tick() is None
    assert effects.execute.call_count == 1
