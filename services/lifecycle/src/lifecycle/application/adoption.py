"""Durable no-change import, separate writer transfer, and controlled relinquishment."""

import json
from collections.abc import Callable
from typing import Any, Protocol
from uuid import uuid4

from lifecycle.application.reservations import Database, Transaction
from lifecycle.domain.admission import digest
from lifecycle.domain.execution import Rejected, identity
from lifecycle.domain.expansion import field_keys, fields, observation, scope, transferable

LOCK = 7709001


class AdoptionOwners(Protocol):
    def observe(
        self, tenant: str, native_scope: dict[str, Any], selected: list[str]
    ) -> dict[str, Any]: ...


def event(
    tx: Transaction,
    subject: str,
    tenant: str,
    actor: str,
    kind: str,
    facts: dict[str, Any],
    now: int,
) -> None:
    tx.execute(
        "INSERT INTO app.expansion_events(subject,tenant,actor,kind,facts,observed_at) "
        "VALUES(%s,%s,%s,%s,%s::jsonb,%s)",
        (subject, tenant, actor, kind, json.dumps(facts), now),
    )


class Adoptions:
    def __init__(
        self, database: Database, owners: AdoptionOwners, clock: Callable[[], int]
    ) -> None:
        self.database, self.owners, self.clock = database, owners, clock

    def current(
        self, tenant: str, native_scope: dict[str, Any], selected: list[str]
    ) -> dict[str, Any]:
        value = self.owners.observe(tenant, native_scope, selected)
        return observation(value, tenant, native_scope, selected, self.clock())

    def read(self, tenant: str, adoption: str) -> dict[str, Any]:
        with self.database.transaction() as tx:
            return self.load(tx, tenant, adoption)

    def load(self, tx: Transaction, tenant: str, adoption: str) -> dict[str, Any]:
        row = tx.one(
            "SELECT * FROM app.adoptions WHERE id=%s AND tenant=%s",
            (identity(adoption), identity(tenant)),
        )
        if row is None:
            raise Rejected("not_found", 404)
        return row

    def create(
        self, tenant: str, actor: str, key: str, native_scope: dict[str, Any], selected: list[str]
    ) -> dict[str, Any]:
        identity(tenant), identity(actor), identity(key)
        scope(native_scope)
        selected = fields(selected)
        fingerprint = digest([native_scope, selected])
        with self.database.transaction() as tx:
            tx.execute("SELECT pg_advisory_xact_lock(%s)", (LOCK,))
            prior = tx.one(
                "SELECT * FROM app.adoptions WHERE tenant=%s AND actor=%s AND command_key=%s",
                (tenant, actor, key),
            )
            if prior:
                if prior["fingerprint"] != fingerprint:
                    raise Rejected("adoption_command_conflict")
                return prior
            baseline = self.current(tenant, native_scope, selected)
            adopted = str(uuid4())
            tx.execute(
                "INSERT INTO "
                "app.adoptions(id,tenant,actor,command_key,scope,fields,fingerprint,"
                "state,baseline) "
                "VALUES(%s,%s,%s,%s,%s::jsonb,%s::jsonb,%s,'observed',%s::jsonb)",
                (
                    adopted,
                    tenant,
                    actor,
                    key,
                    json.dumps(native_scope),
                    json.dumps(selected),
                    fingerprint,
                    json.dumps(baseline),
                ),
            )
            event(
                tx,
                adopted,
                tenant,
                actor,
                "observed",
                {"baseline_sha256": digest(baseline)},
                self.clock(),
            )
            return self.load(tx, tenant, adopted)

    def command(
        self,
        tenant: str,
        adopted: str,
        actor: str,
        key: str,
        revision: int,
        action: str,
        proposed: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        identity(actor), identity(key)
        fingerprint = digest([adopted, revision, action, proposed])
        failure: Rejected | None = None
        with self.database.transaction() as tx:
            tx.execute("SELECT pg_advisory_xact_lock(%s)", (LOCK,))
            prior = tx.one(
                "SELECT * FROM app.expansion_commands WHERE tenant=%s AND actor=%s AND key=%s",
                (tenant, actor, key),
            )
            if prior:
                if prior["fingerprint"] != fingerprint:
                    raise Rejected("adoption_command_conflict")
                return dict(prior["result"])
            row = self.load(tx, tenant, adopted)
            if type(revision) is not int or row["revision"] != revision:
                raise Rejected("adoption_revision_conflict")
            if action not in {"import", "transfer", "detach", "reconcile"}:
                raise Rejected("unsupported_adoption_command", 422)
            try:
                current = self.current(tenant, row["scope"], row["fields"])
                if action != "reconcile" and current["fields"] != row["baseline"]["fields"]:
                    raise Rejected("adoption_drift_held", 423)
                state = row["state"]
                if action == "import":
                    if state != "observed" or proposed != current["fields"]:
                        raise Rejected("adoption_import_must_make_no_changes", 423)
                    for field in field_keys(row["scope"], row["fields"]):
                        if tx.one(
                            "SELECT adoption FROM app.adoption_fields WHERE field_key=%s", (field,)
                        ):
                            raise Rejected("adoption_field_collision", 423)
                    for field in field_keys(row["scope"], row["fields"]):
                        tx.execute(
                            "INSERT INTO app.adoption_fields VALUES(%s,%s)", (field, adopted)
                        )
                    state = "imported"
                elif action == "transfer":
                    if state != "imported":
                        raise Rejected("adoption_no_change_import_required", 423)
                    transferable(current)
                    state = "managed"
                elif action == "reconcile":
                    if state != "held" or current["active_effects"]:
                        raise Rejected("adoption_reconciliation_held", 423)
                    # Re-observation revokes previous authority. Transfer is always separate.
                    state = (
                        "imported"
                        if tx.one(
                            "SELECT adoption FROM app.adoption_fields WHERE adoption=%s", (adopted,)
                        )
                        else "observed"
                    )
                    tx.execute(
                        "UPDATE app.adoptions SET baseline=%s::jsonb WHERE id=%s",
                        (json.dumps(current), adopted),
                    )
                else:
                    if (
                        state == "detached"
                        or current["active_effects"]
                        or not current["transfer_to"]
                        or current["transfer_to"] == current["writer_id"]
                        or current["writer_id"] not in current["fenced_writers"]
                    ):
                        raise Rejected("adoption_detach_transfer_unverified", 423)
                    tx.execute("DELETE FROM app.adoption_fields WHERE adoption=%s", (adopted,))
                    state = "detached"
                tx.execute(
                    "UPDATE app.adoptions SET "
                    "state=%s,revision=revision+1,authority=%s::jsonb WHERE id=%s",
                    (state, json.dumps(current) if state == "managed" else None, adopted),
                )
                event(
                    tx,
                    adopted,
                    tenant,
                    actor,
                    action,
                    {"observation_sha256": digest(current), "state": state},
                    self.clock(),
                )
            except Rejected as error:
                if row["state"] != "detached":
                    tx.execute(
                        "UPDATE app.adoptions SET "
                        "state='held',authority=NULL,revision=revision+1 WHERE id=%s",
                        (adopted,),
                    )
                    event(
                        tx, adopted, tenant, actor, "held", {"reason": error.reason}, self.clock()
                    )
                failure = error
            result = {
                "id": adopted,
                "revision": revision + 1,
                "state": "held" if failure else state,
                "native_write_authorized": False,
            }
            if failure is None:
                tx.execute(
                    "INSERT INTO app.expansion_commands VALUES(%s,%s,%s,%s,%s::jsonb)",
                    (tenant, actor, key, fingerprint, json.dumps(result)),
                )
        if failure:
            raise failure
        return result

    def require_managed(self, tenant: str, adopted: str, selected: list[str]) -> dict[str, Any]:
        failure: Rejected | None = None
        with self.database.transaction() as tx:
            tx.execute("SELECT pg_advisory_xact_lock(%s)", (LOCK,))
            row = self.load(tx, tenant, adopted)
            if row["state"] != "managed" or not set(fields(selected)).issubset(row["fields"]):
                raise Rejected("adoption_write_authority_absent", 423)
            try:
                current = self.current(tenant, row["scope"], row["fields"])
                transferable(current)
                if current["fields"] != row["baseline"]["fields"] or any(
                    current[k] != row["authority"][k]
                    for k in ("epoch", "ownership_revision", "grant_sha256", "writer_id")
                ):
                    raise Rejected("adoption_authority_or_drift_changed", 423)
            except Rejected as error:
                failure = error
                tx.execute(
                    "UPDATE app.adoptions SET "
                    "state='held',authority=NULL,revision=revision+1 WHERE id=%s",
                    (adopted,),
                )
                event(
                    tx,
                    adopted,
                    tenant,
                    str(row["actor"]),
                    "held",
                    {"reason": error.reason},
                    self.clock(),
                )
        if failure:
            raise failure
        return current
