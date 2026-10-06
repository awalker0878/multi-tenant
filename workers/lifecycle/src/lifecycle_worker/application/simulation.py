"""Controlled effect owner. Sealed readback fences late arrivals, including absent effects."""

import json
from collections.abc import Callable
from typing import Any, Protocol


class Transaction(Protocol):
    def execute(self, sql: str, parameters: tuple[Any, ...] = ()) -> Any: ...


class Simulation:
    def __init__(
        self,
        connect: Any,
        redeem: Callable[[dict[str, Any]], dict[str, Any]],
        clock: Callable[[], int],
        custody: Callable[[], str],
    ) -> None:
        self.connect, self.redeem, self.clock, self.custody = connect, redeem, clock, custody

    def execute(self, grant: dict[str, Any]) -> dict[str, Any]:
        if (
            grant.get("simulation") is not True
            or grant.get("adapter") != "p06-simulator-v1"
            or grant.get("epoch") != self.custody()
            or grant.get("expires_at", 0) <= self.clock()
        ):
            raise ValueError("simulation_authority_denied")
        key = (grant["operation_id"], grant["attempt_id"])
        with self.connect() as connection:
            connection.execute("SELECT pg_advisory_xact_lock(7603001)")
            sealed = connection.execute(
                "SELECT * FROM sim.observations WHERE operation_id=%s AND attempt_id=%s", key
            ).fetchone()
            if sealed:
                if sealed["binding"] != self.binding(grant):
                    raise ValueError("effect_binding_conflict")
                if sealed["effect_count"] == 0:
                    raise ValueError("attempt_sealed_absent")
                return {"accepted": True, "duplicate": True}
            # The owner checks current grant authority while serializing acceptance vs sealing.
            decision = self.redeem(grant)
            if (
                decision.get("allowed") is not True
                or decision.get("grant_id") != grant["id"]
                or decision.get("simulation") is not True
                or grant["expires_at"] <= self.clock()
                or grant["epoch"] != self.custody()
            ):
                raise ValueError("grant_denied")
            existing = connection.execute(
                "SELECT * FROM sim.observations WHERE operation_id=%s AND effect_count=1",
                (grant["operation_id"],),
            ).fetchone()
            if existing:
                raise ValueError("logical_effect_already_accepted")
            connection.execute(
                "INSERT INTO sim.observations(operation_id,attempt_id,binding,effect_count,"
                "accepted_at) VALUES(%s,%s,%s::jsonb,1,%s)",
                (*key, json.dumps(self.binding(grant)), self.clock()),
            )
            # Independent writer model: activation transfers authority; no implicit source restart.
            connection.execute(
                "INSERT INTO sim.writers(job,source_writer,target_writer) VALUES(%s,true,false) "
                "ON CONFLICT DO NOTHING",
                (grant["job_id"],),
            )
            if grant["step"] == "activate_target":
                connection.execute(
                    "UPDATE sim.writers SET source_writer=false,target_writer=true WHERE job=%s",
                    (grant["job_id"],),
                )
            if grant["step"] in {"delete_retained_target", "retire_resources"}:
                connection.execute(
                    "UPDATE sim.writers SET source_writer=false,target_writer=false WHERE job=%s",
                    (grant["job_id"],),
                )
        return {"accepted": True, "duplicate": False}

    def reconcile(self, request: dict[str, Any]) -> dict[str, Any]:
        expected = {
            k: request[k]
            for k in (
                "tenant_id",
                "job_id",
                "operation_id",
                "attempt_id",
                "plan_digest",
                "epoch",
                "simulation",
            )
        }
        if expected["simulation"] is not True:
            raise ValueError("simulation_required")
        with self.connect() as connection:
            connection.execute("SELECT pg_advisory_xact_lock(7603001)")
            row = connection.execute(
                "SELECT * FROM sim.observations WHERE operation_id=%s AND attempt_id=%s",
                (request["operation_id"], request["attempt_id"]),
            ).fetchone()
            if row is None:
                connection.execute(
                    "INSERT INTO sim.observations(operation_id,attempt_id,binding,effect_count) "
                    "VALUES(%s,%s,%s::jsonb,0)",
                    (request["operation_id"], request["attempt_id"], json.dumps(expected)),
                )
                count = 0
            else:
                if row["binding"] != expected:
                    raise ValueError("observation_binding_mismatch")
                count = row["effect_count"]
        return {
            **expected,
            "sealed": True,
            "effect_count": count,
            "observed_at": self.clock(),
            "outcome": "confirmed_succeeded" if count else "confirmed_failed",
        }

    def observe(self, request: dict[str, Any]) -> dict[str, Any]:
        expected = self.binding(request)
        with self.connect() as connection:
            row = connection.execute(
                "SELECT * FROM sim.observations WHERE operation_id=%s AND attempt_id=%s",
                (request["operation_id"], request["attempt_id"]),
            ).fetchone()
            if row is None or row["binding"] != expected:
                raise ValueError("observation_absent_or_mismatched")
            count = row["effect_count"]
        return {
            **expected,
            "sealed": True,
            "effect_count": count,
            "observed_at": self.clock(),
            "outcome": "confirmed_succeeded" if count else "confirmed_failed",
        }

    @staticmethod
    def binding(grant: dict[str, Any]) -> dict[str, Any]:
        return {
            k: grant[k]
            for k in (
                "tenant_id",
                "job_id",
                "operation_id",
                "attempt_id",
                "plan_digest",
                "epoch",
                "simulation",
            )
        }
