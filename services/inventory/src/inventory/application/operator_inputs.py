"""Persist attributable operator inputs without granting execution or review authority."""

from collections.abc import Callable
from typing import Any

from inventory.application.configuration import PortingConfiguration
from inventory.application.discovery import Discovery
from inventory.domain.discovery import Actor, Rejected, canonical, digest, identifier, shape
from inventory.domain.operator_inputs import FIELDS, GROUPS, missing_fields, validate_values
from inventory.domain.readiness import (
    METHODS,
    OPERATIONS,
    check_fields,
    requirements,
    validate_context,
)


class OperatorInputs:
    def __init__(
        self, discovery: Discovery, evidence: Callable[..., dict[str, Any]] | None = None
    ) -> None:
        self.discovery = discovery
        self.configuration = PortingConfiguration(discovery)
        self.evidence = evidence

    def readiness(self, actor: Actor) -> dict[str, Any]:
        self.configuration.authorize(actor)
        view = self.read(actor)
        record, config = view["record"], view["configuration"]
        context = None
        platforms: dict[str, str | None] = {"source": None, "target": None}
        with self.discovery.database.transaction() as tx:
            if record:
                row = tx.one(
                    "SELECT payload FROM inventory.operator_input_revisions "
                    "WHERE tenant=%s AND site=%s AND revision=%s",
                    (actor.tenant, actor.site, record["revision"]),
                )
                assert row is not None
                context = row["payload"].get("context")
            if config:
                for side in platforms:
                    endpoint = config[side + "_endpoint"]
                    if endpoint:
                        platforms[side] = self.discovery.endpoint(tx, actor, endpoint)["platform"]
        fields = requirements(context, platforms["source"], platforms["target"])
        values = record["values"] if record else {}
        evidence = (
            self.evidence(
                actor.tenant,
                actor.site,
                record["digest"],
                record["configuration_digest"],
                values,
                self.discovery.clock(),
            )
            if record and self.evidence
            else {}
        )
        stale = bool(record) and (
            "environment_review_changed" in view["holds"]
            or "environment_review_required" in view["holds"]
        )
        checks = check_fields(fields, values, evidence, stale)
        holds = [h for h in view["holds"] if h != "required_operator_inputs_missing"]
        if context is None:
            holds.append("readiness_context_required")
        if context and context["operation"] == "migrate" and not platforms["source"]:
            holds.append("source_environment_required")
        if context and context["operation"] != "discover" and not platforms["target"]:
            holds.append("destination_environment_required")
        missing = [c["field_id"] for c in checks if c["state"] == "missing"]
        if missing:
            holds.append("required_operator_inputs_missing")
        unresolved = [c for c in checks if c["state"] not in {"verified", "not_applicable"}]
        if unresolved:
            holds.append("owner_verification_required")
        return {
            **view,
            "fields": fields,
            "context": context,
            "operations": OPERATIONS,
            "methods": METHODS,
            "platforms": platforms,
            "checks": checks,
            "contexts": [
                {
                    "operation": operation["id"],
                    "method": method,
                    "required_fields": [
                        field["id"]
                        for field in requirements(
                            {"operation": operation["id"], "method": method},
                            platforms["source"],
                            platforms["target"],
                        )
                        if field["required"]
                    ],
                }
                for operation in OPERATIONS
                for method in (METHODS if operation["id"] == "migrate" else [None])
            ],
            "missing_fields": missing,
            "holds": holds,
            "collection_complete": bool(record and context) and not missing and not stale,
            "evidence_current": bool(record and context) and not holds,
        }

    def read(self, actor: Actor) -> dict[str, Any]:
        self.configuration.authorize(actor)
        with self.discovery.database.transaction() as tx:
            row = tx.one(
                "SELECT * FROM inventory.operator_input_revisions WHERE tenant=%s AND site=%s "
                "ORDER BY revision DESC LIMIT 1",
                (actor.tenant, actor.site),
            )
            config = self.configuration.view(tx, actor)["configuration"]
            record = (
                None
                if row is None
                else {
                    "revision": row["revision"],
                    "digest": row["digest"],
                    "values": row["payload"]["values"],
                    "configuration_digest": row["payload"]["configuration_digest"],
                    "saved_at": row["created_at"],
                }
            )
            missing = missing_fields(record["values"] if record else {})
            holds = []
            if missing:
                holds.append("required_operator_inputs_missing")
            if not config or not config["confirmation_current"]:
                holds.append("environment_review_required")
            if record and record["configuration_digest"] != (config["digest"] if config else None):
                holds.append("environment_review_changed")
            return {
                "tenant_id": actor.tenant,
                "site_id": actor.site,
                "groups": GROUPS,
                "fields": FIELDS,
                "record": record,
                "configuration": None
                if config is None
                else {
                    k: config[k]
                    for k in (
                        "revision",
                        "digest",
                        "source_endpoint",
                        "target_endpoint",
                        "confirmation_current",
                    )
                },
                "missing_fields": missing,
                "holds": holds,
                "collection_complete": bool(record) and not holds,
                "native_write_authorized": False,
            }

    def command(
        self,
        actor: Actor,
        operation: str,
        body: dict[str, Any],
        key: str,
        target: str | None = None,
        expected: int | None = None,
    ) -> dict[str, Any]:
        self.configuration.authorize(actor)
        identifier(key)
        if (
            operation not in {"operator_inputs_save", "operator_readiness_save"}
            or target is not None
        ):
            raise Rejected("invalid_operation")
        shape(
            body,
            {"values", "configuration_digest"}
            | ({"context"} if operation == "operator_readiness_save" else set()),
        )
        if operation == "operator_readiness_save":
            validate_context(body["context"])
        validate_values(body["values"])
        bound = digest([operation, actor.site, expected, body])
        d = self.discovery
        with d.database.transaction() as tx:
            tx.execute("SELECT pg_advisory_xact_lock(7404001)")
            prior = tx.one(
                "SELECT * FROM inventory.commands WHERE tenant=%s AND actor=%s AND command_key=%s",
                (actor.tenant, actor.actor, key),
            )
            if prior:
                if prior["digest"] != bound:
                    raise Rejected("idempotency_conflict", 409)
                return dict(prior["result"])
            row = tx.one(
                "SELECT * FROM inventory.operator_input_revisions WHERE tenant=%s AND site=%s "
                "ORDER BY revision DESC LIMIT 1",
                (actor.tenant, actor.site),
            )
            if row and expected is None:
                raise Rejected("revision_required", 428)
            if expected != (row["revision"] if row else None):
                raise Rejected("stale_revision", 412)
            configuration = tx.one(
                "SELECT digest FROM inventory.porting_revisions WHERE tenant=%s AND site=%s "
                "ORDER BY revision DESC LIMIT 1",
                (actor.tenant, actor.site),
            )
            if body["configuration_digest"] != (configuration["digest"] if configuration else None):
                raise Rejected("environment_review_changed", 412)
            revision = row["revision"] + 1 if row else 1
            packet_digest = digest([actor.tenant, actor.site, revision, body])
            tx.execute(
                "INSERT INTO inventory.operator_input_revisions VALUES "
                "(%s,%s,%s,%s::jsonb,%s,%s,%s)",
                (
                    actor.tenant,
                    actor.site,
                    revision,
                    canonical(body),
                    packet_digest,
                    actor.actor,
                    d.clock(),
                ),
            )
            result = {
                "revision": revision,
                "digest": packet_digest,
                "native_write_authorized": False,
            }
            d.record(tx, actor.tenant, actor.actor, operation, actor.site or "", result)
            tx.execute(
                "INSERT INTO inventory.commands VALUES (%s,%s,%s,%s,%s::jsonb)",
                (actor.tenant, actor.actor, key, bound, canonical(result)),
            )
            return result
