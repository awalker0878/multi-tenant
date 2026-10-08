"""A05/A13: real SQL races, cross-tenant physical pools and retained unknown outcomes."""

from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from typing import Any
from uuid import uuid4

import pytest

from lifecycle.application.placement_reservations import PlacementReservations
from lifecycle.application.reservations import Held
from lifecycle.domain.admission import digest
from lifecycle.infrastructure.store import Postgres

NOW = 2_000_000_000


class Snapshots:
    def __init__(self) -> None:
        self.now = NOW
        self.in_use = False
        self.accounted: list[str] = []
        self.withdrawn_tenants: set[str] = set()
        self.used = {"vcpus": 0, "memory_mib": 0, "storage_gib": 0, "addresses": 0}
        self.pool_id = digest({"provider_id": "physical-provider", "native_ref": "physical-host"})

    def pools(self, request: dict[str, Any]) -> list[dict[str, Any]]:
        return [
            {
                "id": self.pool_id,
                "provider_id": "physical-provider",
                "native_ref": "physical-host",
                "observed_at": self.now,
                "expires_at": self.now + 30,
                "exclusive_owner": "lifecycle-resource-owner",
                "native_lease_id": "fixture-lease",
                "lease_expires_at": self.now + 3600,
                "policy_sha256": request["policy_sha256"],
                "allowed_tenants": (
                    [] if request["scope"]["tenant_id"] in self.withdrawn_tenants
                    else [request["scope"]["tenant_id"]]
                ),
                "limits": {"vcpus": 8, "memory_mib": 8192, "storage_gib": 80, "addresses": 2},
                "provider_used": self.used,
                "accounted_reservation_ids": self.accounted,
            }
        ]

    def allocation(self, request: dict[str, Any], reservation_id: str) -> dict[str, Any]:
        return {
            "reservation_id": reservation_id,
            "plan_digest": request["plan_digest"],
            "placement_sha256": request["placement_sha256"],
            "observed_at": self.now,
            "expires_at": self.now + 30,
            "outcome": "known",
            "in_use": self.in_use,
            "allocations_absent": not self.in_use,
            "allocations_sha256": digest(request["allocations"]),
        }


def request(source: Snapshots, cpu: int = 8) -> dict[str, Any]:
    allocations = [
        {
            "pool_id": source.pool_id,
            "native_ref": "physical-host",
            "workload_id": str(uuid4()),
            "vector": {
                "vcpus": cpu,
                "memory_mib": cpu * 1024,
                "storage_gib": cpu * 10,
                "addresses": cpu // 4,
            },
        }
    ]
    return {
        "scope": {"tenant_id": str(uuid4())},
        "plan_digest": digest(str(uuid4())),
        "generation_id": str(uuid4()),
        "policy_sha256": "a" * 64,
        "placement_sha256": digest(allocations),
        "allocations": allocations,
    }


def test_two_tenants_compete_for_one_atomic_vector(database: Postgres) -> None:
    source = Snapshots()
    service = PlacementReservations(database, source, lambda: source.now)
    requests = [request(source), request(source)]
    with ThreadPoolExecutor(2) as pool:
        receipts = list(pool.map(lambda r: service.reserve(r["scope"]["tenant_id"], r), requests))
    assert sorted(r["state"] for r in receipts) == ["denied", "reserved"]
    with database.transaction() as tx:
        row = tx.one("SELECT count(*) AS n FROM app.placement_debits")
        assert row is not None
        assert row["n"] == 1
    winner = next(
        r
        for r in requests
        if any(p["plan_digest"] == r["plan_digest"] and p["state"] == "reserved" for p in receipts)
    )
    restarted = PlacementReservations(database, source, lambda: source.now)
    replay = restarted.reserve(winner["scope"]["tenant_id"], winner)
    assert replay["state"] == "reserved"
    changed = deepcopy(winner)
    changed["allocations"][0]["vector"]["vcpus"] = 1
    with pytest.raises(Held, match="conflict"):
        restarted.reserve(winner["scope"]["tenant_id"], changed)


def test_expiry_retains_debits_and_confirmed_usage_is_counted_once(database: Postgres) -> None:
    source = Snapshots()
    service = PlacementReservations(database, source, lambda: source.now)
    first = request(source, 4)
    accepted = service.reserve(first["scope"]["tenant_id"], first)
    source.in_use = True
    source.used = first["allocations"][0]["vector"]
    source.accounted = [accepted["reservation_id"]]
    service.transition(first["scope"]["tenant_id"], first["plan_digest"], "confirm")
    second = request(source, 4)
    assert service.reserve(second["scope"]["tenant_id"], second)["state"] == "reserved"
    source.now += 400
    assert (
        service.check(first["scope"]["tenant_id"], first["plan_digest"])["state"] == "expired_held"
    )
    with pytest.raises(Held, match="live_or_unknown"):
        service.transition(first["scope"]["tenant_id"], first["plan_digest"], "release")
    third = request(source, 4)
    assert service.reserve(third["scope"]["tenant_id"], third)["state"] == "denied"


def test_provider_usage_drift_revokes_previous_readback_without_freeing_debits(
    database: Postgres,
) -> None:
    source = Snapshots()
    service = PlacementReservations(database, source, lambda: source.now)
    selected = request(source, 4)
    accepted = service.reserve(selected["scope"]["tenant_id"], selected)
    assert accepted["state"] == "reserved"
    source.used = {
        "vcpus": 6, "memory_mib": 6144, "storage_gib": 60, "addresses": 2,
    }
    with pytest.raises(Held, match="provider_capacity_changed"):
        service.check(selected["scope"]["tenant_id"], selected["plan_digest"])
    # No silent compensating delete or speculative release on changed facts.
    with database.transaction() as tx:
        debit = tx.one(
            "SELECT count(*) AS n FROM app.placement_debits WHERE reservation=%s",
            (accepted["reservation_id"],),
        )
        assert debit is not None and debit["n"] == 1


def test_provider_tenant_authorization_withdrawal_rejects_current_receipt(
    database: Postgres,
) -> None:
    source = Snapshots()
    service = PlacementReservations(database, source, lambda: source.now)
    selected = request(source, 4)
    assert service.reserve(selected["scope"]["tenant_id"], selected)["state"] == "reserved"
    source.withdrawn_tenants.add(selected["scope"]["tenant_id"])
    with pytest.raises(Held, match="native_authority_unavailable"):
        service.check(selected["scope"]["tenant_id"], selected["plan_digest"])
