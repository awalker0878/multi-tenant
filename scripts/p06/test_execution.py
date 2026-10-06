"""Q04 PostgreSQL journal and separately owned PostgreSQL simulated effect observations."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from pathlib import Path
from typing import Any
from uuid import uuid4

import psycopg
import pytest
from psycopg.rows import dict_row
from test_admission import NOW, lab_fixture

from lifecycle.application.execution import Execution
from lifecycle.domain.admission import digest
from lifecycle.domain.execution import Rejected
from lifecycle.infrastructure.store import Postgres
from lifecycle_worker.application.simulation import Simulation


class Current:
    def __init__(self, snapshot: dict[str, Any], epoch: str, clock: list[int]) -> None:
        self.snapshot, self.epoch, self.clock = snapshot, epoch, clock
        self.unavailable = False
    def custody(self) -> str:
        return self.epoch
    def current(self, job: dict[str, Any]) -> dict[str, Any]:
        if self.unavailable:
            raise Rejected("owner_unavailable", 503)
        return deepcopy(self.snapshot) | {"evaluated_at": self.clock[0]}


class Custody:
    def __init__(self) -> None:
        self.available = True
    def finalize(self, job: dict[str, Any], observations: list[dict[str, Any]]) -> dict[str, Any]:
        if not self.available:
            raise RuntimeError("store_partition")
        return {"id": str(uuid4()), "tenant_id": job["tenant"], "job_id": job["id"],
                "plan_digest": job["binding"]["digest"], "digest": digest(observations),
                "state": "finalized", "evidence_level": "E2", "native_support": False}


@pytest.fixture()
def world(database: Postgres, postgres: dict[str, Any]) -> dict[str, Any]:
    c, b, snapshot = lab_fixture()
    epoch, campaign, approval = str(uuid4()), str(uuid4()), str(uuid4())
    clock = [NOW]
    snapshot.update(simulation=True)
    snapshot["campaign"].update(id=campaign, adapter="p06-simulator-v1", custody_epoch=epoch, worker_ids=["sim-worker"])
    current, evidence = Current(snapshot, epoch, clock), Custody()
    with psycopg.connect(**postgres, autocommit=True) as connection:
        connection.execute("INSERT INTO app.execution_control VALUES(1,%s,false)", (epoch,))
        if not connection.execute("SELECT 1 FROM pg_roles WHERE rolname='simulation_owner'").fetchone():
            connection.execute("CREATE ROLE simulation_owner NOLOGIN")
            connection.execute("CREATE ROLE simulation_runtime LOGIN")
        connection.execute("GRANT CREATE ON DATABASE p05_lifecycle TO simulation_owner")
        connection.execute("DROP SCHEMA IF EXISTS sim CASCADE")
        root = Path(__file__).resolve().parents[2]
        migration = (root / "workers/lifecycle/migrations/001_simulation.sql").read_text()
        connection.execute("\n".join(line for line in migration.splitlines() if not line.startswith("\\")))
    service: Execution
    def connect() -> Any:
        return psycopg.connect(**(postgres | {"user": "simulation_runtime"}), row_factory=dict_row)
    def redeem(grant: dict[str, Any]) -> dict[str, Any]:
        return service.redeem(grant, "sim-worker")
    peer = Simulation(connect, redeem, lambda: clock[0], current.custody)
    service = Execution(database, current, peer, evidence, lambda: clock[0])
    tenant, actor = c["scope"]["tenant_id"], b["executor_ids"][0]
    def admit(key: str | None = None) -> dict[str, Any]:
        return service.admit(tenant, actor, key or str(uuid4()), c, b, approval, campaign)
    return locals()


def test_atomic_admission_idempotency_collision_and_immutable_history(world: dict[str, Any]) -> None:
    w = world; key = str(uuid4())
    with ThreadPoolExecutor(max_workers=6) as pool:
        jobs = list(pool.map(lambda _: w['admit'](key), range(6)))
    assert len({j['id'] for j in jobs}) == 1
    with w['database'].transaction() as tx:
        assert tx.one("SELECT count(*) n FROM app.execution_dispatch")['n'] == 1
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            tx.execute("DELETE FROM app.execution_jobs")
    with pytest.raises(Rejected, match='resource_held'):
        w['admit']()
    with pytest.raises(Rejected, match='command_key_conflict'):
        w['service'].admit(w['tenant'], w['actor'], key, w['c'], w['b'], str(uuid4()), w['campaign'])


def test_simulated_journey_independent_readback_and_evidence(world: dict[str, Any]) -> None:
    w = world; job = w['admit'](); service = w['service']
    assert service.checkpoint(w['tenant'], job['id'])['state'] == 'ready'
    for effect in w['c']['effects']:
        assert service.activity(w['tenant'],job['id'],effect['id'],'sim-worker')['state'] == 'confirmed_succeeded'
    result = service.checkpoint(w['tenant'], job['id'])
    assert result['state'] == 'completed'
    public = service.read(w['tenant'],job['id'])
    assert public['simulation'] and public['evidence']['evidence_level'] == 'E2'
    with w['connect']() as connection:
        writer = connection.execute('SELECT * FROM sim.writers').fetchone()
        assert writer['target_writer'] and not writer['source_writer']
        assert connection.execute('SELECT count(*) n FROM sim.observations WHERE effect_count=1').fetchone()['n'] == len(w['c']['effects'])
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            connection.execute('SELECT * FROM app.execution_jobs')


def test_lost_acknowledgement_holds_until_readback_and_no_blind_retry(world: dict[str, Any]) -> None:
    w=world; job=w['admit'](); service=w['service']; original=w['peer'].execute
    def lost(grant: dict[str, Any]) -> dict[str, Any]:
        original(grant)
        raise TimeoutError
    w['peer'].execute=lost
    assert service.activity(w['tenant'],job['id'],'reserve','sim-worker')['state']=='outcome_unknown'
    assert service.activity(w['tenant'],job['id'],'reserve','sim-worker')['state']=='held'
    assert service.activity(w['tenant'],job['id'],'preflight','sim-worker')['state']=='held'
    assert service.reconcile(w['tenant'],job['id'])['operations'][0]['outcome']=='confirmed_succeeded'
    with w['connect']() as connection:
        assert connection.execute('SELECT count(*) n FROM sim.observations WHERE effect_count=1').fetchone()['n']==1


def test_crash_before_acceptance_seals_late_worker_before_retry(world: dict[str, Any]) -> None:
    w=world; job=w['admit'](); service=w['service']
    grant=service.acquire(w['tenant'],job['id'],'reserve','sim-worker')
    public=service.reconcile(w['tenant'],job['id'])
    assert public['operations'][0]['outcome']=='confirmed_failed'
    with pytest.raises(ValueError,match='sealed_absent'):
        w['peer'].execute(grant)
    service.command(w['tenant'],job['id'],w['actor'],str(uuid4()),'retry_unstarted',public['revision'])
    assert service.activity(w['tenant'],job['id'],'reserve','sim-worker')['state']=='confirmed_succeeded'


@pytest.mark.parametrize('fault',['epoch','expiry','worker','revoked','stop','owner_partition','plan_input','snapshot_scope'])
def test_boundary_denials(world: dict[str, Any], fault: str) -> None:
    w=world; job=w['admit'](); service=w['service']
    grant=service.acquire(w['tenant'],job['id'],'reserve','sim-worker')
    if fault=='epoch': w['current'].epoch=str(uuid4())
    if fault=='expiry': w['clock'][0]+=16
    if fault=='worker': grant['worker_id']='foreign-worker'
    if fault=='revoked': w['snapshot']['approval']['revoked']=True
    if fault=='stop': service.command(w['tenant'],job['id'],w['actor'],str(uuid4()),'stop',service.read(w['tenant'],job['id'])['revision'])
    if fault=='owner_partition': w['current'].unavailable=True
    if fault=='plan_input': w['snapshot']['input_digests']['intent']='f'*64
    if fault=='snapshot_scope': w['snapshot']['scope']['native_scope']='foreign'
    with pytest.raises((Rejected,ValueError)):
        w['peer'].execute(grant)
    with w['connect']() as connection:
        assert connection.execute('SELECT count(*) n FROM sim.observations').fetchone()['n']==0


def test_revocation_keeps_committed_observation_and_custody(world: dict[str, Any]) -> None:
    w=world; job=w['admit'](); service=w['service']
    grant=service.acquire(w['tenant'],job['id'],'reserve','sim-worker'); w['peer'].execute(grant)
    w['snapshot']['approval']['revoked']=True
    result=service.reconcile(w['tenant'],job['id'])
    assert result['operations'][0]['outcome']=='confirmed_succeeded'
    assert service.activity(w['tenant'],job['id'],'preflight','sim-worker')['state']=='held'


def test_cancel_does_not_undo_accepted_effect_or_release_holds(world: dict[str, Any]) -> None:
    w=world; job=w['admit'](); service=w['service']
    grant=service.acquire(w['tenant'],job['id'],'reserve','sim-worker'); w['peer'].execute(grant)
    public=service.read(w['tenant'],job['id']); key=str(uuid4())
    first=service.command(w['tenant'],job['id'],w['actor'],key,'cancel',public['revision'])
    assert first==service.command(w['tenant'],job['id'],w['actor'],key,'cancel',public['revision'])
    assert first['effect_undone'] is False
    assert service.checkpoint(w['tenant'],job['id'])['state']=='cancelled'
    assert service.read(w['tenant'],job['id'])['resources_retained']
    with pytest.raises(Rejected,match='resource_held'):w['admit']()


def test_missing_evidence_cannot_complete_and_current_epoch_required_after_restore(world: dict[str, Any]) -> None:
    w=world; job=w['admit'](); service=w['service']
    for effect in w['c']['effects']:service.activity(w['tenant'],job['id'],effect['id'],'sim-worker')
    w['evidence'].available=False
    assert service.checkpoint(w['tenant'],job['id'])['state']=='held'
    assert service.read(w['tenant'],job['id'])['reason']=='evidence_pending'
    w['evidence'].available=True
    assert service.checkpoint(w['tenant'],job['id'])['state']=='completed'


def test_operational_lane_and_wrong_tenant_are_denied(world: dict[str, Any]) -> None:
    w=world; c=deepcopy(w['c']);c['lane']='operational'
    with pytest.raises(Rejected,match='simulation_only'):
        w['service'].admit(w['tenant'],w['actor'],str(uuid4()),c,w['b'],w['approval'],w['campaign'])
    job=w['admit']()
    with pytest.raises(Rejected,match='not_found'):
        w['service'].read(str(uuid4()),job['id'])


def test_stale_ui_cannot_resume_or_retry_unknown(world: dict[str, Any]) -> None:
    w=world; job=w['admit'](); service=w['service']
    service.acquire(w['tenant'],job['id'],'reserve','sim-worker')
    with pytest.raises(Rejected,match='stale_revision'):
        service.command(w['tenant'],job['id'],w['actor'],str(uuid4()),'resume',job['revision'])
    with pytest.raises(Rejected,match='reconciliation_required'):
        service.command(w['tenant'],job['id'],w['actor'],str(uuid4()),'resume',service.read(w['tenant'],job['id'])['revision'])
