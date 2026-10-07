"""P08 replay, data and single-writer invariants; synthetic owners with real PostgreSQL."""

from copy import deepcopy
from typing import Any
from uuid import uuid4

import psycopg
import pytest
from test_native_workflow import Owners, plan

from lifecycle.application.native_workflow import NativeWorkflow
from lifecycle.domain.admission import digest
from lifecycle.domain.execution import Rejected
from lifecycle.domain.migration import cases, stages, validate
from lifecycle.domain.native_workflow import observations, validate_plan


def migration(mode: str = "cutover", method: str = "VM_COLD_EXPORT") -> dict[str, Any]:
    dataset = str(uuid4())
    return {
        "schema_version": 2,
        "review": {"revision": 1, "digest": digest("review")},
        "owner_inputs_sha256": digest({"fixture": "owner"}),
        "mode": mode,
        "method": method,
        **{
            side: {
                "profile_sha256": digest(side),
                "native_identity_sha256": digest(side + "id"),
                "tuple_sha256": digest(side + "tuple"),
                "observed_at": 990,
                "expires_at": 1900,
            }
            for side in ("source", "target")
        },
        "datasets": [dataset],
        "disks": [
            {
                "source_disk_sha256": digest("disk"),
                "target_key": str(uuid4()),
                "capacity_bytes": 1024,
                "format": "qcow2",
                "datasets": [dataset],
            }
        ],
        "delta": {
            "kind": {
                "VM_COLD_EXPORT": "none",
                "VM_SNAPSHOT_BASELINE_APP_DELTA": "application",
                "VM_SNAPSHOT_BASELINE_FILE_DELTA": "file",
                "APPLICATION_REBUILD_RESTORE": "restore",
                "EXTERNAL_BLOCK_REPLICATION": "block",
            }[method],
            "requires_running_guest": method
            in {"VM_SNAPSHOT_BASELINE_APP_DELTA", "VM_SNAPSHOT_BASELINE_FILE_DELTA"},
            "qualification_sha256": digest("delta"),
        },
        "artifacts": {
            k: digest(k)
            for k in ("capture", "transfer", "conversion", "guest", "delta", "recovery")
        },
        "objectives": {
            "owner_id": str(uuid4()),
            "acceptance_sha256": digest("objectives"),
            "max_outage_seconds": 3600,
            "max_data_loss_bytes": 0,
        },
        "rehearsal_sha256": digest("rehearsal") if mode == "cutover" else None,
        "recovery_of_sha256": digest("source")
        if mode in {"rollback", "forward_recovery", "reverse_recovery", "cleanup"}
        else None,
    }


def migration_plan(mode: str = "cutover", method: str = "VM_COLD_EXPORT") -> dict[str, Any]:
    p = plan()
    m = migration(mode, method)
    p.update(
        schema_version=2, purpose="migrate", migration=m, intents={s: digest(s) for s in stages(m)}
    )
    return p


def migration_input(p: dict[str, Any]) -> dict[str, Any]:
    m = p["migration"]
    return {
        "tenant_id": p["scope"]["tenant_id"],
        "site_id": p["scope"]["site_id"],
        **m["review"],
        "method": m["method"],
        "source": m["source"],
        "target": m["target"],
        "objectives": m["objectives"],
        "current": True,
        "native_write_authorized": False,
        "owner_inputs": {"fixture": "owner"},
        "target_disk_formats": ["raw", "qcow2"],
        "datasets": [{"id": d, "disk_keys": [2000]} for d in m["datasets"]],
        "disks": [
            {
                "native_sha256": d["source_disk_sha256"],
                "capacity_bytes": d["capacity_bytes"],
                "key": 2000,
            }
            for d in m["disks"]
        ],
    }


@pytest.mark.parametrize(
    "fault",
    ["missing", "stale", "tenant", "review", "disk", "dataset", "capacity", "owner", "format"],
)
def test_current_profile_booleans_cannot_replace_exact_inventory_bindings(fault: str) -> None:
    from lifecycle.domain.migration import current_profiles

    p = migration_plan()
    evidence = migration_input(p)
    current_profiles(p, evidence, 1000)
    if fault == "missing":
        evidence = {}
    elif fault == "stale":
        evidence["current"] = False
    elif fault == "tenant":
        evidence["tenant_id"] = str(uuid4())
    elif fault == "review":
        evidence["revision"] += 1
    elif fault == "disk":
        evidence["disks"] = []
    elif fault == "dataset":
        evidence["datasets"][0]["disk_keys"] = [2001]
    elif fault == "capacity":
        evidence["disks"][0]["capacity_bytes"] += 1
    elif fault == "owner":
        evidence["owner_inputs"] = {"fixture": "changed"}
    else:
        evidence["target_disk_formats"] = []
    with pytest.raises(Rejected):
        current_profiles(p, evidence, 1000)


class MigrationOwners(Owners):
    def current(self, p: dict[str, Any], binding: dict[str, Any]) -> dict[str, Any]:
        return super().current(p, binding) | {
            "migration_input": migration_input(p),
            "migration_sha256": digest(p["migration"]),
            "source_profile_current": True,
            "target_profile_current": True,
            "migration_method_qualified": True,
            "all_datasets_accounted": True,
        }

    def observe(
        self, p: dict[str, Any], binding: dict[str, Any], phase: str
    ) -> list[dict[str, Any]]:
        return [
            {
                "case": case,
                "phase": phase,
                "binding_sha256": digest(binding),
                "intent_digest": p["intents"][binding["stage"]],
                "observer_id": self.observer,
                "observed_at": self.now,
                "expires_at": self.now + 30,
                "outcome": "passed",
                "evidence_sha256": digest([case, binding]),
                "policy_results": {c["id"]: c["expectation"] for c in p["policy_cases"]}
                if case == "policy_paths"
                else {},
                **self.evidence_changes,
            }
            for case in cases(p, binding["stage"], phase)
            if case != self.omit
        ]


@pytest.fixture
def control(
    database: Any, postgres: dict[str, Any]
) -> tuple[NativeWorkflow, MigrationOwners, dict[str, Any]]:
    p = migration_plan()
    with psycopg.connect(**postgres) as c:
        c.execute("INSERT INTO app.native_control VALUES(1,%s,false)", (p["epoch"],))
    owners = MigrationOwners(p)
    return NativeWorkflow(database, owners, lambda: owners.now), owners, p


def advance(
    control: NativeWorkflow, p: dict[str, Any], job: str, until: str | None = None
) -> dict[str, Any]:
    for stage in stages(p["migration"]):
        grant = control.prepare(p["scope"]["tenant_id"], job, stage)
        assert grant["native_binding"]["operation_plan_sha256"] == p["intents"][stage]
        control.boundary(p["scope"]["tenant_id"], grant, p["executor_id"], "before_api_sequence")
        if stage == until:
            return grant
        control.reconcile(p["scope"]["tenant_id"], grant)
    return grant


def recovery(p: dict[str, Any], job: str, mode: str) -> dict[str, Any]:
    new = deepcopy(p)
    new.update(source_job_id=job, approval_id=str(uuid4()), plan_digest=digest(str(uuid4())))
    new["custody_generation"] += 1
    new["migration"].update(mode=mode, recovery_of_sha256=digest(p), rehearsal_sha256=None)
    new["intents"] = {s: digest(s) for s in stages(new["migration"])}
    return new


@pytest.mark.parametrize(
    "method",
    [
        "VM_COLD_EXPORT",
        "VM_SNAPSHOT_BASELINE_APP_DELTA",
        "VM_SNAPSHOT_BASELINE_FILE_DELTA",
        "APPLICATION_REBUILD_RESTORE",
        "EXTERNAL_BLOCK_REPLICATION",
    ],
)
def test_explicit_method_and_delta_order(method: str) -> None:
    p = migration_plan(method=method)
    validate_plan(p, 1000)
    ordered = stages(p["migration"])
    assert (
        ordered.index("final_sync")
        < ordered.index("shutdown_source")
        < ordered.index("admit_writes")
    )
    assert ("restart_baseline_source" in ordered) == (
        method in {"VM_SNAPSHOT_BASELINE_APP_DELTA", "VM_SNAPSHOT_BASELINE_FILE_DELTA"}
    )


@pytest.mark.parametrize(
    "mutation",
    [
        "empty",
        "unmapped",
        "duplicate_disk",
        "same_target",
        "expired",
        "fallback",
        "guest_delta",
        "rehearsal",
    ],
)
def test_incomplete_or_unsafe_plan_held(mutation: str) -> None:
    m = migration()
    if mutation == "empty":
        m["datasets"] = []
    if mutation == "unmapped":
        m["datasets"].append(str(uuid4()))
    if mutation == "duplicate_disk":
        m["disks"].append(deepcopy(m["disks"][0]))
    if mutation == "same_target":
        m["target"] = deepcopy(m["source"])
    if mutation == "expired":
        m["source"]["expires_at"] = 1000
    if mutation == "fallback":
        m["method"] = "automatic"
    if mutation == "guest_delta":
        m["delta"]["requires_running_guest"] = True
    if mutation == "rehearsal":
        m["rehearsal_sha256"] = None
    with pytest.raises(Rejected):
        validate(m, 1000)


def test_cutover_complete_and_write_marker_append_only(
    control: Any, postgres: dict[str, Any]
) -> None:
    service, owners, p = control
    job = service.admit(p, str(uuid4()))
    advance(service, p, job)
    assert service.read(p["scope"]["tenant_id"], job)["state"] == "migrated"
    with psycopg.connect(**(postgres | {"user": "lifecycle_runtime"})) as c:
        row = c.execute(
            "SELECT count(*) FROM app.native_migration_writes WHERE job=%s", (job,)
        ).fetchone()
        assert row is not None and row[0] == 1
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            c.execute("DELETE FROM app.native_migration_writes WHERE job=%s", (job,))


def test_lost_activation_response_forbids_rollback_and_stale_worker(control: Any) -> None:
    service, owners, p = control
    job = service.admit(p, str(uuid4()))
    grant = advance(service, p, job, "admit_writes")
    service.hold(p["scope"]["tenant_id"], job)
    with pytest.raises(Rejected, match="target_writes_require_reconciliation"):
        service.admit(recovery(p, job, "rollback"), str(uuid4()))
    new = recovery(p, job, "forward_recovery")
    recovered = service.admit(new, str(uuid4()))
    with pytest.raises(Rejected):
        service.boundary(p["scope"]["tenant_id"], grant, p["executor_id"], "during_api_sequence")
    advance(service, new, recovered)
    assert service.read(p["scope"]["tenant_id"], recovered)["state"] == "recovered"
    with pytest.raises(Rejected, match="target_writes_require_reconciliation"):
        service.admit(recovery(new, recovered, "rollback"), str(uuid4()))


def test_prewrite_rollback_requires_no_divergence_and_recovery_replaces_authority(
    control: Any,
) -> None:
    service, owners, p = control
    job = service.admit(p, str(uuid4()))
    advance(service, p, job, "validate_target")
    new = recovery(p, job, "rollback")
    recovered = service.admit(new, str(uuid4()))
    owners.omit = "no_target_divergence"
    stage = "fence_target"
    grant = service.prepare(p["scope"]["tenant_id"], recovered, stage)
    service.boundary(p["scope"]["tenant_id"], grant, p["executor_id"], "before_api_sequence")
    service.reconcile(p["scope"]["tenant_id"], grant)
    grant = service.prepare(p["scope"]["tenant_id"], recovered, "verify_no_divergence")
    service.boundary(p["scope"]["tenant_id"], grant, p["executor_id"], "before_api_sequence")
    with pytest.raises(Rejected):
        service.reconcile(p["scope"]["tenant_id"], grant)
    with pytest.raises(Rejected):
        service.prepare(p["scope"]["tenant_id"], recovered, "restore_source")


def test_partial_fencing_never_admits_target_writes(control: Any) -> None:
    service, owners, p = control
    job = service.admit(p, str(uuid4()))
    advance(service, p, job, "validate_target")
    checkpoint = service.checkpoint(p["scope"]["tenant_id"], job)
    service.reconcile(p["scope"]["tenant_id"], checkpoint["grant"])
    owners.omit = "all_source_writers_fenced"
    with pytest.raises(Rejected):
        service.prepare(p["scope"]["tenant_id"], job, "admit_writes")


def test_rehearsal_has_no_business_write_stage() -> None:
    m = migration("rehearsal")
    assert "admit_writes" not in stages(m)
    assert "business_effects_suppressed" in cases({"migration": m}, "rehearsal_validate", "before")


def test_migration_proof_is_independent_and_exact() -> None:
    p = migration_plan()
    binding = {"stage": "capture"}
    owner = MigrationOwners(p)
    proof = owner.observe(p, binding, "after")
    observations(p, binding, "after", proof, 1000)
    proof[0]["observer_id"] = p["executor_id"]
    with pytest.raises(Rejected):
        observations(p, binding, "after", proof, 1000)
