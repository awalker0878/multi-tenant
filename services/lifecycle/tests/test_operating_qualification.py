"""P10 E2 load and real database restore. Owners/native effects are synthetic."""

import json
import os
import subprocess
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any
from uuid import uuid4

import psycopg
import pytest
from test_expansion import EnterpriseOwner, spec
from test_native_workflow import Owners, plan

from lifecycle.application.enterprise import Enterprise
from lifecycle.application.native_workflow import NativeWorkflow
from lifecycle.domain.admission import digest
from lifecycle.domain.execution import Rejected


def test_shared_endpoint_load_fairness_backpressure_and_revocation(database: Any) -> None:
    tenants = [str(uuid4()) for _ in range(12)]
    endpoint = str(uuid4())
    tenant_pools = {digest({"tenant": t}) for t in tenants}

    class LoadOwner(EnterpriseOwner):
        def budgets(self, pools: list[str]) -> dict[str, Any]:
            values = super().budgets(pools)
            for pool, value in values.items():
                value["limit"] = 1 if pool in tenant_pools else 4
            return values

    owner = LoadOwner()
    app = Enterprise(database, owner, lambda: owner.now)
    for tenant in tenants:
        app.create(tenant, str(uuid4()), str(uuid4()), [spec(tenant, endpoint) for _ in range(4)])
    sequence: list[str] = []
    samples: list[dict[str, Any]] = []
    start = time.monotonic_ns()
    for _ in range(12):
        with ThreadPoolExecutor(max_workers=8) as pool:
            claims = [c for c in pool.map(lambda _: app.claim(), range(8)) if c]
        assert len(claims) == 4
        assert len({c["tenant_id"] for c in claims}) == 4
        assert app.claim() is None  # Saturation holds; no new accepted effects.
        owner.deny = True
        for claim in claims:
            with pytest.raises(Rejected, match="owner_revoked"):
                app.boundary(claim["tenant_id"], claim["operation_id"], claim["lease"])
        owner.deny = False
        for claim in claims:
            begin = time.monotonic_ns()
            app.boundary(claim["tenant_id"], claim["operation_id"], claim["lease"])
            result = app.reconcile(claim["tenant_id"], claim["operation_id"], claim["lease"])
            samples.append(
                {
                    "id": claim["operation_id"],
                    "tenant_id": claim["tenant_id"],
                    "start_ns": begin,
                    "end_ns": time.monotonic_ns(),
                    "outcome": result["state"],
                }
            )
            sequence.append(claim["tenant_id"])
        counts = Counter(sequence)
        # Equal work and budgets: no tenant is more than one completed turn ahead.
        assert max(counts[t] for t in tenants) - min(counts[t] for t in tenants) <= 1
    end = time.monotonic_ns()
    assert len(set(s["id"] for s in samples)) == 48
    assert Counter(sequence) == {t: 4 for t in tenants}
    assert app.claim() is None
    with database.transaction() as tx:
        assert tx.one("SELECT COUNT(*) AS n FROM app.enterprise_allocations")["n"] == 0
        assert tx.one("SELECT COUNT(*) AS n FROM app.enterprise_object_holds")["n"] == 0
    if destination := os.environ.get("P10_MEASUREMENTS_DIR"):
        output = Path(destination)
        output.mkdir(parents=True, exist_ok=True)
        (output / "scheduler.json").write_text(
            json.dumps(
                {
                    "scope": "synthetic_native_owners_real_postgresql",
                    "boundary": "boundary_authorization_through_independent_reconcile",
                    "tenants": tenants,
                    "start_ns": start,
                    "end_ns": end,
                    "records": samples,
                    "shared_endpoint_limit": 4,
                    "dispatchers": 8,
                    "capacity_claim": False,
                },
                indent=2,
            )
            + "\n"
        )


def test_restored_old_database_cannot_repeat_an_accepted_effect(
    database: Any, postgres: dict[str, Any], tmp_path: Path
) -> None:
    p = plan()
    with psycopg.connect(**postgres) as connection:
        connection.execute("INSERT INTO app.native_control VALUES(1,%s,false)", (p["epoch"],))
    owner = Owners(p)
    workflow = NativeWorkflow(database, owner, lambda: owner.now)
    tenant = p["scope"]["tenant_id"]
    job = workflow.admit(p, str(uuid4()))
    grant = workflow.prepare(tenant, job, "reserve")
    conn = psycopg.conninfo.make_conninfo(**postgres)
    pg = Path(os.environ["P05_POSTGRES_BIN"])
    backup = tmp_path / "before-effect.dump"
    subprocess.run(
        [str(pg / "pg_dump"), "--format=custom", "--file", str(backup), "--dbname", conn],
        check=True,
        capture_output=True,
        timeout=30,
    )
    workflow.boundary(tenant, grant, p["executor_id"], "before_effect")
    external_effects = [grant["operation_id"]]
    # Custody stays independent of the restored database and fences the old generation.
    owner.current_epoch = str(uuid4())
    started = time.monotonic_ns()
    subprocess.run(
        [
            str(pg / "pg_restore"),
            "--clean",
            "--if-exists",
            "--exit-on-error",
            "--dbname",
            conn,
            str(backup),
        ],
        check=True,
        capture_output=True,
        timeout=30,
    )
    restored = NativeWorkflow(database, owner, lambda: owner.now)
    with pytest.raises(Rejected, match="custody"):
        restored.boundary(tenant, grant, p["executor_id"], "before_effect")
    with pytest.raises(Rejected):
        restored.prepare(tenant, job, "reserve")
    assert external_effects == [grant["operation_id"]]
    if destination := os.environ.get("P10_MEASUREMENTS_DIR"):
        (Path(destination) / "stale-restore.json").write_text(
            json.dumps(
                {
                    "scope": "single_lifecycle_database_real_pg_dump_restore_synthetic_custody",
                    "restore_and_denial_ms": (time.monotonic_ns() - started) / 1e6,
                    "old_grant_denied": True,
                    "accepted_synthetic_effects": len(external_effects),
                    "native_write_authorized": False,
                    "full_control_plane_rto_claim": False,
                }
            )
            + "\n"
        )
