"""Scoped, owner-reviewed application flows mapped to existing native destination IDs.

No source ACL becomes an application dependency. No browser-supplied observation
can establish policy equivalence or positive/negative traffic measurements.
"""
from copy import deepcopy
from typing import Any

from planning.application.planning import Planning
from planning.domain.model import Actor, Rejected, canonical, digest, identifier, integer, shape
from planning.domain.network_evidence import (
    FLOW_KEYS, isolation_checks, native_application_flow_choices,
    network_checks,
)
from planning.domain.operational_evidence import snapshot
from planning.domain.qualification import verified

SCOPE_SQL = (
    "tenant=%s AND actor=%s AND application=%s AND environment=%s AND site=%s"
)


class MigrationFlows:
    def __init__(self, planning: Planning) -> None:
        self.planning = planning

    @staticmethod
    def scope(actor: Actor, site: str) -> tuple[str, str, str, str, str]:
        return (identifier(actor.tenant), identifier(actor.actor),
                identifier(actor.application), identifier(actor.environment),
                identifier(site))

    def current(self, actor: Actor, site: str, delegation: str) -> dict[str, Any]:
        """Re-read independently authorized current Catalogue, Inventory and Assurance.

        An older stored assessment cannot authorize a choice after a source or
        destination owner changes. We never fall back to a prior assessment
        when the newest one is ambiguous or revoked.
        """
        scoped = self.scope(actor, site)
        if not isinstance(delegation, str) or not delegation:
            raise Rejected("application_flow_delegation_required", 403)
        with self.planning.database.transaction() as tx:
            rows = tx.all(
                "SELECT payload FROM app.planning_records WHERE tenant=%s AND "
                "actor=%s AND application=%s AND environment=%s AND "
                "kind='assessment' ORDER BY created_at DESC,id DESC LIMIT 10",
                scoped[:4],
            )
        candidates = [
            row["payload"] for row in rows
            if row["payload"].get("action") == "application.migrate"
            and any(item.get("site_id") == site
                    for item in row["payload"].get("candidates", []))
        ]
        if not candidates:
            raise Rejected("application_migration_assessment_required", 423)
        retained = candidates[0]
        matches = [i for i, item in enumerate(retained["candidates"])
                   if item.get("site_id") == site]
        if len(matches) != 1 or len(retained.get("inputs", [])) != len(retained["candidates"]):
            raise Rejected("application_flow_scope_ambiguous", 423)
        index = matches[0]
        candidate = retained["candidates"][index]
        original = retained["inputs"][index]
        current_intent, current_inputs = self.planning.sources.resolve(
            actor, retained["intent"]["id"], [candidate], {site: delegation},
            retained["action"], retained["method"],
        )
        if (digest(current_intent) != digest(retained["intent"])
                or not isinstance(current_inputs, list) or len(current_inputs) != 1):
            raise Rejected("application_flow_source_intent_changed", 423)
        facts = current_inputs[0]
        if any(digest(facts[k]) != digest(original[k]) for k in ("destination", "policy", "profile")):
            # New destination observations require re-assessment before owner
            # choices can be offered, rather than copying the previous result.
            raise Rejected("application_flow_destination_assessment_stale", 423)
        dest, qualification, policy = (
            facts["destination"], facts["qualification"], facts["policy"]
        )
        now = self.planning.clock()
        if (
            not verified(qualification, now)
            or qualification.get("status") != "qualified"
            or qualification.get("revoked") is not False
            or not isinstance(dest.get("site_id"), str)
            or dest["site_id"] != site
        ):
            raise Rejected("application_flow_independent_qualification_required", 423)
        observed = snapshot(dest, qualification, now)
        if not isinstance(observed, dict) or not isinstance(observed.get("network"), dict):
            raise Rejected("application_flow_current_native_evidence_required", 423)
        intent = current_intent["intent"]
        choices = native_application_flow_choices(intent, observed["network"], policy)
        context_sha = digest({
            "assessment": retained["id"],
            "intent": current_intent["digest"],
            "destination": digest(dest),
            "qualification": digest(qualification),
            "policy": digest(policy),
            "network": digest(observed["network"]),
        })
        expires = min(
            dest["capability_snapshot"]["expires_at"],
            qualification["verification"]["expires_at"],
            policy["expires_at"], now + 60,
        )
        return {
            "intent": intent, "destination": dest, "policy": policy,
            "data": observed, "choices": choices,
            "context_sha256": context_sha, "expires_at": expires,
        }

    def _read_saved(self, actor: Actor, site: str) -> dict[str, Any] | None:
        with self.planning.database.transaction() as tx:
            row = tx.one(
                "SELECT revision,context_sha256,payload,updated_at "
                "FROM app.planning_application_flow_reviews WHERE " + SCOPE_SQL,
                self.scope(actor, site),
            )
        return row

    @staticmethod
    def evaluate(current: dict[str, Any], selections: Any, now: int) -> list[str]:
        choices, data = current["choices"], deepcopy(current["data"])
        if not isinstance(selections, list) or len(selections) > 512:
            raise Rejected("invalid_application_flow_selection")
        allowed = {row["source_flow_id"]: row for row in choices}
        if len(allowed) != len(choices):
            raise Rejected("ambiguous_application_flow_intent")
        seen: set[str] = set()
        bound: dict[str, Any] = {}
        network = data["network"]
        observer = network.get("observer_principal")
        writer = network.get("writer_principal")
        if (
            not isinstance(observer, str) or not observer
            or not isinstance(writer, str) or not writer or observer == writer
            or current["expires_at"] <= now
        ):
            return ["independent_native_flow_observer_required"]
        for selection in selections:
            if not isinstance(selection, dict) or set(selection) != {
                "source_flow_id", "rule_native_ref", "route_native_ref"
            }:
                raise Rejected("invalid_application_flow_selection")
            flow_id = selection["source_flow_id"]
            if (not isinstance(flow_id, str) or flow_id not in allowed
                    or flow_id in seen):
                raise Rejected("unapproved_application_flow")
            option = allowed[flow_id]
            if (selection["rule_native_ref"] not in option["destination_firewall_rule_ids"]
                    or selection["route_native_ref"] not in option["destination_route_ids"]):
                raise Rejected("unobserved_application_flow_destination")
            seen.add(flow_id)
            bound[flow_id] = {
                "rule_native_ref": selection["rule_native_ref"],
                "route_native_ref": selection["route_native_ref"],
                "observer_principal": observer,
                "observed_at": now,
                "expires_at": current["expires_at"],
                "policy_sha256": digest(current["policy"]),
                "topology_sha256": network["topology_sha256"],
            }
        missing = [row["source_flow_id"] for row in choices if row["required"]
                   and row["source_flow_id"] not in seen]
        if missing:
            return ["application_flow_required_selection_missing"]
        # Application-owner selection is an overlay for assessment, never an
        # alteration to the native observed snapshot's asserted reality.
        network["application_flow_selections"] = bound
        check_data = dict(data)
        check_data["network"] = network
        try:
            checks = network_checks(current["intent"], check_data, current["policy"], now)
            checks += isolation_checks(
                current["intent"], current["destination"], check_data,
                current["policy"], now,
            )
        except (KeyError, ValueError, TypeError, IndexError):
            return ["application_flow_independent_evidence_incomplete"]
        return sorted({
            reason for _, status, reason, mandatory in checks
            if mandatory and status != "eligible"
        })

    def read(self, actor: Actor, site: str, delegation: str) -> dict[str, Any]:
        current = self.current(actor, site, delegation)
        saved = self._read_saved(actor, site)
        changed = saved is not None and saved["context_sha256"] != current["context_sha256"]
        selections = saved["payload"]["selections"] if saved and not changed else []
        holds = self.evaluate(current, selections, self.planning.clock())
        if changed:
            holds = ["application_flow_evidence_changed", *holds]
        return {
            "context_sha256": current["context_sha256"],
            "revision": saved["revision"] if saved else 0,
            "expires_at": current["expires_at"],
            "choices": current["choices"],
            "selections": selections,
            "holds": list(dict.fromkeys(holds)),
            "status": ("invalidated" if changed else
                       "held" if holds else "eligible"),
            "native_write_authorized": False,
        }

    def save(
        self, actor: Actor, site: str, delegation: str, body: dict[str, Any], key: str
    ) -> dict[str, Any]:
        shape(body, {"site_id", "revision", "context_sha256", "selections"})
        if body["site_id"] != site:
            raise Rejected("application_flow_site_mismatch", 403)
        revision = integer(body["revision"], 0, 1000000)
        identifier(key)
        current = self.current(actor, site, delegation)
        if body["context_sha256"] != current["context_sha256"]:
            raise Rejected("application_flow_evidence_changed", 412)
        holds = self.evaluate(current, body["selections"], self.planning.clock())
        canonical(body)
        if len(canonical(body).encode()) > 32768:
            raise Rejected("application_flow_payload_bound", 413)
        fingerprint = digest({"operation": "migration_flow_save", "site": site, "body": body})
        with self.planning.database.transaction() as tx:
            tx.execute("SELECT pg_advisory_xact_lock(7504001)")
            prior = self.planning.retry(tx, actor, key, fingerprint)
            if prior:
                return prior
            old = tx.one(
                "SELECT revision FROM app.planning_application_flow_reviews "
                "WHERE " + SCOPE_SQL, self.scope(actor, site),
            )
            if (old["revision"] if old else 0) != revision:
                raise Rejected("application_flow_revision_changed", 412)
            outcome = {
                "revision": revision + 1,
                "status": "held" if holds else "eligible",
                "holds": holds,
                "native_write_authorized": False,
            }
            tx.execute(
                "INSERT INTO app.planning_application_flow_reviews "
                "(tenant,actor,application,environment,site,revision,context_sha256,payload,updated_at) "
                "VALUES(%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s) "
                "ON CONFLICT (tenant,actor,application,environment,site) "
                "DO UPDATE SET revision=excluded.revision,"
                "context_sha256=excluded.context_sha256,"
                "payload=excluded.payload,updated_at=excluded.updated_at",
                (*self.scope(actor, site), revision + 1, current["context_sha256"],
                 canonical({"selections": body["selections"]}), self.planning.clock()),
            )
            tx.execute(
                "INSERT INTO app.planning_commands "
                "(tenant,actor,command_key,fingerprint,response,created_at) "
                "VALUES(%s,%s,%s,%s,%s::jsonb,%s)",
                (actor.tenant, actor.actor, key, fingerprint,
                 canonical(outcome), self.planning.clock()),
            )
        return outcome

    def require(self, actor: Actor, site: str) -> None:
        """Execution-side fail-closed gate; no owner delegation is minted here."""
        saved = self._read_saved(actor, site)
        if saved is None or saved["payload"].get("selections") is None:
            raise Rejected("approved_application_flow_selection_required", 423)
        # A site-bound approval cannot be enough without a fresh native proof.
        if self.planning.clock() - saved["updated_at"] > 60:
            raise Rejected("application_flow_evidence_expired", 423)
        if saved["payload"].get("holds"):
            raise Rejected("application_flow_not_eligible", 423)
