"""P04/Q02 identity, fencing, immutable observation, tenancy and scheduler qualification."""

import copy
import hashlib
import json
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path
from typing import Any

import psycopg
import pytest

from inventory.application.discovery import Discovery, uid
from inventory.application.ports import Transaction
from inventory.application.views import InventoryViews
from inventory.domain.discovery import (
    DIMENSIONS,
    Actor,
    EnrollmentPolicy,
    Rejected,
    Worker,
    profile,
)
from inventory.infrastructure.policies import parse_policy
from inventory.infrastructure.store import Postgres

TOKEN = "worker-" + "a" * 64


def row(tx: Transaction, query: str) -> dict[str, Any]:
    result = tx.one(query)
    assert result is not None
    return result


def policy_document() -> dict[str, Any]:
    return {
        "policy_id": uid(),
        "tenant": uid(),
        "site": uid(),
        "owner": uid(),
        "worker": uid(),
        "worker_fingerprint": hashlib.sha256(TOKEN.encode()).hexdigest(),
        "epoch": uid(),
        "platform": "openstack",
        "native_scope": "project-a",
        "authority": "shared-cloud",
        "installed": {
            "product": "fixture-only",
            "api": "compute-2.1",
            "backend": "unassessed",
            "features": [],
            "entitlements": [],
            "configuration_reference": "synthetic-test",
        },
        "streams": [
            {
                "kind": kind,
                "base_url": "https://native.example"
                + (
                    "/v3/project-a"
                    if kind == "volume"
                    else "/v2.0"
                    if kind == "network"
                    else "/v2.1"
                ),
                "addresses": ["127.0.0.1"],
                "ca_file": "/synthetic/ca.pem",
                "credential_file": "/synthetic/token",
                "api_version": "3.0" if kind == "volume" else "2.0" if kind == "network" else "2.1",
            }
            for kind in ("server", "network", "volume")
        ],
        "freshness_seconds": 300,
        "requests_per_minute": 60,
        "concurrency": 2,
        "tenant_concurrency": 1,
        "max_pages": 50,
        "expires_at": time.time() + 3600,
        "coverage_reference": "synthetic-permission-observer",
    }


class PolicySet:
    def __init__(self, policy: EnrollmentPolicy) -> None:
        self.values = {policy.policy_id: policy}

    def load(self) -> dict[str, EnrollmentPolicy]:
        return self.values


class Campaign:
    def __init__(self, postgres: dict[str, Any]) -> None:
        self.database = Postgres(postgres | {"user": "inventory_runtime"})
        self.policy = parse_policy(policy_document())
        self.policies = PolicySet(self.policy)
        self.now = time.time()
        self.held = False
        self.service = Discovery(self.database, self.policies, self.admit, lambda: self.now)
        self.actor = Actor(
            self.policy.tenant, self.policy.owner, uid(), "inventory.admin", self.policy.site
        )
        self.worker = Worker(self.policy.worker, self.policy.worker_fingerprint)
        self.endpoint = self.service.command(
            self.actor, "enroll", {"policy_id": self.policy.policy_id, "label": "Test site"}, uid()
        )["endpoint_id"]

    def admit(self, policy: EnrollmentPolicy) -> None:
        if self.held:
            raise Rejected("collection_authority_unavailable", 503)

    def start(self) -> str:
        return str(
            self.service.command(
                replace(self.actor, action="inventory.discover"),
                "discover",
                {},
                uid(),
                self.endpoint,
            )["discovery_id"]
        )

    def page(
        self, lease: dict[str, Any], items: list[dict[str, Any]], terminal: bool = True
    ) -> dict[str, Any]:
        return {
            "discovery_id": lease["discovery_id"],
            "lease_token": lease["lease_token"],
            "sequence": lease["sequence"],
            "observations": items,
            "next_cursor": None if terminal else items[-1]["native_id"],
            "terminal": terminal,
            "coverage": True,
            "collected_at": self.now,
            "error": None,
        }

    def item(
        self, kind: str = "server", native: str = "vm-a", incarnation: str | None = "creation-a"
    ) -> dict[str, Any]:
        return {
            "kind": kind,
            "native_id": native,
            "incarnation": incarnation,
            "name": "Observed server",
            "scope": self.policy.native_scope,
            "facts": {"status": "ACTIVE"},
        }

    def complete(self, items: list[dict[str, Any]] | None = None) -> str:
        job = self.start()
        for stream in range(3):
            self.now += 2
            lease = self.service.claim(self.worker)["job"]
            assert lease and lease["stream"] == stream
            result = self.service.submit(
                self.worker,
                self.page(
                    lease, (items if items is not None else [self.item()]) if stream == 0 else []
                ),
            )
        assert result["status"] == "complete"
        return job

    def resources(self, job: str) -> dict[str, Any]:
        return InventoryViews(self.service).read(
            replace(self.actor, action="inventory.read"), "resources", job
        )


@pytest.fixture
def campaign(postgres: dict[str, Any]) -> Campaign:
    sqls = [p.read_text() for p in sorted((Path(__file__).parents[1] / "migrations").glob("*.sql"))]
    with psycopg.connect(**postgres, autocommit=True) as connection:
        connection.execute("DROP SCHEMA IF EXISTS inventory CASCADE")
        connection.execute("SET ROLE inventory_owner")
        for sql in sqls:
            connection.execute(sql)
            connection.execute(sql)  # Actual replay, not a schema-text assertion.
    return Campaign(postgres)


@pytest.mark.parametrize("platform", ["vmware", "openstack", "ahv"])
def test_all_profile_dimensions_are_explicit_without_support_claims(platform: str) -> None:
    facts = profile(platform, {"api": "declared"})
    assert tuple(facts["dimensions"]) == DIMENSIONS
    assert all(x["state"] == "UNASSESSED" for x in facts["dimensions"].values())
    assert facts["native_write_authorized"] is False


@pytest.mark.parametrize(
    "mutation",
    ["unknown", "http", "credentials", "link_local", "scope", "boolean_budget", "missing_stream"],
)
def test_policy_rejects_scope_and_egress_broadening(mutation: str) -> None:
    p = policy_document()
    if mutation == "unknown":
        p["admin_password"] = "denied"
    if mutation == "http":
        p["streams"][0]["base_url"] = "http://native.example"
    if mutation == "credentials":
        p["streams"][0]["base_url"] = "https://a:b@native.example"
    if mutation == "link_local":
        p["streams"][0]["addresses"] = ["169.254.169.254"]
    if mutation == "scope":
        p["native_scope"] = "project-a&all_tenants=1"
    if mutation == "boolean_budget":
        p["concurrency"] = True
    if mutation == "missing_stream":
        p["streams"].pop()
    with pytest.raises(Rejected):
        parse_policy(p)


def test_receipts_and_current_role_precede_retries(campaign: Campaign) -> None:
    c = campaign
    key = uid()
    actor = replace(c.actor, action="inventory.discover")
    a = c.service.command(actor, "discover", {}, key, c.endpoint)
    assert c.service.command(actor, "discover", {}, key, c.endpoint) == a
    with pytest.raises(Rejected, match="idempotency_conflict"):
        c.service.command(actor, "discover", {"arbitrary": True}, key, c.endpoint)
    with pytest.raises(Rejected, match="action_denied"):
        c.service.command(replace(actor, action="inventory.read"), "discover", {}, key, c.endpoint)


def test_concurrent_identical_command_has_one_job(campaign: Campaign) -> None:
    c = campaign
    key = uid()

    def issue(_: int) -> dict[str, Any]:
        return c.service.command(
            replace(c.actor, action="inventory.discover"), "discover", {}, key, c.endpoint
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(issue, range(2)))
    assert results[0] == results[1]
    with c.database.transaction() as tx:
        assert row(tx, "SELECT count(*) AS n FROM inventory.jobs")["n"] == 1


def test_complete_generation_identity_restart_and_expiry(campaign: Campaign) -> None:
    c = campaign
    first = c.complete()
    resource = c.resources(first)["items"][0]
    assert resource["holds"] == [] and resource["reserved"] is False
    assert resource["ownership"] == "observation_only"
    c.service = Discovery(c.database, c.policies, c.admit, lambda: c.now)
    second = c.complete()
    assert c.resources(second)["items"][0]["resource_id"] == resource["resource_id"]
    assert "historical_generation" in c.resources(first)["items"][0]["holds"]
    c.now += 301
    assert "expired" in c.resources(second)["items"][0]["holds"]
    rows = InventoryViews(c.service).read(replace(c.actor, action="inventory.read"), "endpoints")[
        "items"
    ]
    assert rows[0]["state"] == "held" and rows[0]["reason"] == "expired"


def test_partial_pages_do_not_replace_current_or_tombstone(campaign: Campaign) -> None:
    c = campaign
    first = c.complete()
    c.start()
    c.now += 2
    lease = c.service.claim(c.worker)["job"]
    body = c.page(lease, [])
    body["coverage"] = False
    assert c.service.submit(c.worker, body)["status"] == "partial"
    with c.database.transaction() as tx:
        resource_row = row(tx, "SELECT * FROM inventory.resources")
        assert not resource_row["tombstone"] and resource_row["absent_count"] == 0
        assert (
            str(row(tx, "SELECT current_generation FROM inventory.endpoints")["current_generation"])
            == first
        )


def test_two_complete_absences_and_reused_id_never_inherit_identity(campaign: Campaign) -> None:
    c = campaign
    c.complete()
    c.complete([])
    with c.database.transaction() as tx:
        assert row(tx, "SELECT tombstone FROM inventory.resources")["tombstone"] is False
    c.complete([])
    with c.database.transaction() as tx:
        assert row(tx, "SELECT tombstone FROM inventory.resources")["tombstone"] is True
    last = c.complete([c.item(incarnation="recreated")])
    assert "identity_ambiguous" in c.resources(last)["items"][0]["holds"]


def test_page_fencing_same_receipt_and_changed_replay(campaign: Campaign) -> None:
    c = campaign
    c.start()
    lease = c.service.claim(c.worker)["job"]
    body = c.page(lease, [c.item()])
    first = c.service.submit(c.worker, body)
    assert c.service.submit(c.worker, body) == first
    changed = copy.deepcopy(body)
    changed["observations"][0]["name"] = "changed"
    with pytest.raises(Rejected, match="page_retry_conflict"):
        c.service.submit(c.worker, changed)
    c.now += 2
    old = c.service.claim(c.worker)["job"]
    c.now += 31
    new = c.service.claim(c.worker)["job"]
    assert new["lease_token"] != old["lease_token"]
    with pytest.raises(Rejected, match="stale_lease"):
        c.service.submit(c.worker, c.page(old, []))


@pytest.mark.parametrize("kind", ["scope", "duplicate", "cursor", "timestamp", "unknown_field"])
def test_hostile_pages_never_publish(campaign: Campaign, kind: str) -> None:
    c = campaign
    c.start()
    lease = c.service.claim(c.worker)["job"]
    body = c.page(lease, [c.item()])
    if kind == "scope":
        body["observations"][0]["scope"] = "foreign"
    if kind == "duplicate":
        body["observations"] *= 2
    if kind == "cursor":
        body["next_cursor"] = "http://metadata/"
    if kind == "timestamp":
        body["collected_at"] += 300
    if kind == "unknown_field":
        body["tenant_id"] = uid()
    with pytest.raises(Rejected):
        c.service.submit(c.worker, body)
    with c.database.transaction() as tx:
        assert row(tx, "SELECT count(*) AS n FROM inventory.pages")["n"] == 0


def test_revocation_and_governance_hold_stop_dispatch_and_result(campaign: Campaign) -> None:
    c = campaign
    c.start()
    c.held = True
    assert c.service.claim(c.worker) == {"job": None, "retry_after": 5}
    c.held = False
    c.now += 6
    lease = c.service.claim(c.worker)["job"]
    c.held = True
    with pytest.raises(Rejected, match="collection_authority"):
        c.service.submit(c.worker, c.page(lease, []))
    c.held = False
    c.service.command(c.actor, "revoke", {}, uid(), c.endpoint, 1)
    with pytest.raises(Rejected, match="enrollment_unavailable"):
        c.service.submit(c.worker, c.page(lease, []))
    assert c.service.claim(c.worker)["job"] is None


def test_renewal_and_foreign_guessed_ids(campaign: Campaign) -> None:
    c = campaign
    c.service.command(c.actor, "revoke", {}, uid(), c.endpoint, 1)
    with pytest.raises(Rejected, match="stale_revision"):
        c.service.command(c.actor, "renew", {}, uid(), c.endpoint, 1)
    assert c.service.command(c.actor, "renew", {}, uid(), c.endpoint, 2)["revision"] == 3
    foreign = replace(c.actor, tenant=uid(), action="inventory.discover")
    with pytest.raises(Rejected, match="not_found"):
        c.service.command(foreign, "discover", {}, uid(), c.endpoint)
    generation = c.complete()
    with pytest.raises(Rejected, match="not_found"):
        InventoryViews(c.service).read(
            replace(foreign, action="inventory.read"), "resources", generation
        )


def test_owner_collisions_are_proposals_and_cannot_grant_ownership(campaign: Campaign) -> None:
    c = campaign
    job = c.complete()
    resource = c.resources(job)["items"][0]["resource_id"]
    for _ in range(2):
        result = c.service.command(
            replace(c.actor, action="inventory.match"),
            "match",
            {
                "resource_id": resource,
                "application_id": uid(),
                "intent_revision": uid(),
                "generation_id": job,
            },
            uid(),
            c.endpoint,
        )
        assert result["ownership_granted"] is False
    assert "ownership_collision" in c.resources(job)["items"][0]["holds"]


def test_runtime_cannot_rewrite_pages_history_receipts_or_audit(campaign: Campaign) -> None:
    c = campaign
    c.complete()
    for table in ("pages", "commands", "observations", "audit", "outbox", "matches"):
        with pytest.raises(psycopg.errors.InsufficientPrivilege), c.database.transaction() as tx:
            tx.execute("DELETE FROM inventory." + table)


def test_rate_budget_and_shared_endpoint_fairness(campaign: Campaign) -> None:
    c = campaign
    p2 = replace(c.policy, policy_id=uid(), tenant=uid(), owner=uid(), native_scope="project-b")
    c.policies.values[p2.policy_id] = p2
    a2 = replace(c.actor, tenant=p2.tenant, actor=p2.owner)
    ep2 = c.service.command(
        a2, "enroll", {"policy_id": p2.policy_id, "label": "Second tenant"}, uid()
    )["endpoint_id"]
    c.start()
    c.service.command(replace(a2, action="inventory.discover"), "discover", {}, uid(), ep2)
    seen = []
    for _ in range(4):
        lease = c.service.claim(c.worker)["job"]
        seen.append(lease["endpoint_id"])
        c.service.submit(c.worker, c.page(lease, []))
        assert c.service.claim(c.worker)["job"] is None
        c.now += 1.01
    assert seen[0] != seen[1] and seen[0] == seen[2] and seen[1] == seen[3]


def test_interrupted_pages_resume_without_false_completeness(campaign: Campaign) -> None:
    c = campaign
    c.start()
    lease = c.service.claim(c.worker)["job"]
    c.service.submit(c.worker, c.page(lease, [c.item()], terminal=False))
    c.service = Discovery(c.database, c.policies, c.admit, lambda: c.now)
    c.now += 2
    resumed = c.service.claim(c.worker)["job"]
    assert resumed["cursor"] == "vm-a" and resumed["sequence"] == 1
    assert c.resources(lease["discovery_id"])["completion"] == "running"
    assert c.resources(lease["discovery_id"])["items"] == []


def test_outbox_uncertainty_preserves_identity_and_order_after_revocation(
    campaign: Campaign,
) -> None:
    from inventory.application.events import publish_one

    c = campaign
    c.complete()
    delivered: list[dict[str, Any]] = []

    def uncertain(fact: dict[str, Any]) -> None:
        delivered.append(fact)
        raise RuntimeError("lost confirmation")

    with pytest.raises(RuntimeError, match="lost confirmation"):
        publish_one(c.database, uncertain)
    c.held = True
    assert publish_one(c.database, delivered.append)
    assert delivered[0] == delivered[1]
    while publish_one(c.database, delivered.append):
        pass
    assert [v["sequence"] for v in delivered[1:]] == sorted(v["sequence"] for v in delivered[1:])
    assert not publish_one(c.database, delivered.append)
    assert all(v["tenant_id"] == c.actor.tenant for v in delivered)
    assert TOKEN not in json.dumps(delivered)


def test_expired_early_page_finishes_partial_without_replacing_current(campaign: Campaign) -> None:
    c = campaign
    original = c.complete()
    job = c.start()
    for index in range(3):
        c.now += 301 if index == 1 else 2
        lease = c.service.claim(c.worker)["job"]
        result = c.service.submit(c.worker, c.page(lease, []))
    assert result["status"] == "partial"
    with c.database.transaction() as tx:
        assert (
            str(row(tx, "SELECT current_generation FROM inventory.endpoints")["current_generation"])
            == original
        )
    assert c.resources(job)["reason"] == "generation_expired"


def test_unavailable_tenant_cannot_starve_a_shared_worker(campaign: Campaign) -> None:
    c = campaign
    p2 = replace(c.policy, policy_id=uid(), tenant=uid(), owner=uid(), native_scope="project-b")
    c.policies.values[p2.policy_id] = p2
    other = replace(c.actor, tenant=p2.tenant, actor=p2.owner)
    endpoint = c.service.command(
        other, "enroll", {"policy_id": p2.policy_id, "label": "Other"}, uid()
    )["endpoint_id"]
    c.start()
    c.now += 0.01
    c.service.command(replace(other, action="inventory.discover"), "discover", {}, uid(), endpoint)

    def authority(policy: EnrollmentPolicy) -> None:
        if policy.tenant == c.policy.tenant:
            raise Rejected("collection_authority_unavailable", 503)

    c.service.collection_authority = authority
    assert c.service.claim(c.worker)["job"] is None
    assert c.service.claim(c.worker)["job"]["endpoint_id"] == endpoint


def test_concurrent_claims_respect_tenant_budget_across_authorities(campaign: Campaign) -> None:
    c = campaign
    p2 = replace(c.policy, policy_id=uid(), authority="separate-cloud")
    c.policies.values[p2.policy_id] = p2
    endpoint = c.service.command(
        c.actor, "enroll", {"policy_id": p2.policy_id, "label": "Other authority"}, uid()
    )["endpoint_id"]
    c.start()
    c.service.command(
        replace(c.actor, action="inventory.discover"), "discover", {}, uid(), endpoint
    )
    with ThreadPoolExecutor(max_workers=4) as pool:
        claims = list(pool.map(lambda _: c.service.claim(c.worker), range(4)))
    assert sum(claim["job"] is not None for claim in claims) == 1


def test_retry_exhaustion_emits_original_terminal_fact(campaign: Campaign) -> None:
    c = campaign
    job = c.start()
    for failure in range(3):
        lease = c.service.claim(c.worker)["job"]
        body = c.page(lease, [])
        body["error"] = "throttled"
        result = c.service.submit(c.worker, body)
        assert result["status"] == ("partial" if failure == 2 else "queued")
        assert c.service.claim(c.worker)["job"] is None
        c.now += 10
    with c.database.transaction() as tx:
        fact = tx.one(
            "SELECT * FROM inventory.outbox WHERE aggregate=%s "
            "AND event_type='inventory.discovery.completed'",
            (job,),
        )
        assert fact is not None and fact["payload"]["reason"] == "throttled"
    assert c.resources(job)["completion"] == "partial"
