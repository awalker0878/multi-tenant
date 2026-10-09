"""Scoped, owner-reviewed application flows mapped to existing native destination IDs.

No source ACL becomes an application dependency. No browser-supplied observation
can establish policy equivalence or positive/negative traffic measurements.
"""
from copy import deepcopy
from collections.abc import Callable
from typing import Any

from planning.application.planning import Planning
from planning.domain.model import Actor, Rejected, canonical, digest, identifier, integer, shape
from planning.domain.network_evidence import (
    isolation_checks, native_application_flow_choices,
    network_checks,
)
from planning.domain.effective_security import qualify as qualify_effective_security
from planning.domain.security_boundary import compare as compare_policy_boundary
from planning.domain.operational_evidence import inventory_digest, snapshot
from planning.domain.qualification import binding_digest, verified

SCOPE_SQL = (
    "tenant=%s AND application=%s AND environment=%s AND site=%s AND assessment_id=%s"
)


class MigrationFlows:
    def __init__(
        self, planning: Planning,
        execution_proof: Callable[[Actor, str, dict[str, Any], int], None] | None = None,
    ) -> None:
        self.planning = planning
        self.execution_proof = execution_proof

    @staticmethod
    def scope(actor: Actor, site: str) -> tuple[str, str, str, str]:
        return (identifier(actor.tenant), identifier(actor.application),
                identifier(actor.environment), identifier(site))

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
                "application=%s AND environment=%s AND "
                "kind='assessment' AND payload->>'action'='application.migrate' "
                "AND payload->'candidates' @> %s::jsonb "
                "ORDER BY created_at DESC,id DESC LIMIT 1",
                (*scoped[:3], canonical([{"site_id": site}])),
            )
        if len(rows) != 1:
            raise Rejected("application_migration_assessment_required", 423)
        retained = rows[0]["payload"]
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
        # Fresh observation generations are expected. Preserve reviewed native
        # selections across telemetry refreshes, but never accept changes to
        # the commissioned platform, native scope or profile/policy definition.
        if (digest(facts["policy"]) != digest(original["policy"])
                or digest(facts["profile"]) != digest(original["profile"])
                or any(facts["destination"].get(k) != original["destination"].get(k)
                       for k in ("tenant_id", "site_id", "endpoint_id", "native_scope",
                                 "platform", "installed_tuple"))):
            raise Rejected("application_flow_destination_identity_changed", 423)
        dest, qualification, policy = (
            facts["destination"], facts["qualification"], facts["policy"]
        )
        now = self.planning.clock()
        if (
            dest.get("current") is not True
            or dest.get("completion") != "complete"
            or dest.get("holds")
            or dest.get("installed_provenance") != "observed"
            or type(dest.get("expires_at")) is not int
            or dest["expires_at"] <= now
            or dest.get("generation_id") != candidate["generation_id"]
        ):
            raise Rejected("application_flow_destination_generation_not_current", 423)
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
        if dest.get("platform") in {"vmware", "ahv"}:
            cases = observed.get("effective_security_cases")
            accepted = qualification.get("capabilities", {}).get(
                "migration.effective_security", {}
            )
            if (
                qualification.get("evidence_level") != "E4"
                or not isinstance(accepted, dict)
                or accepted.get("status") != "supported"
                or not isinstance(cases, list)
                or len(cases) > 512
                or digest(cases) not in accepted.get("values", [])
            ):
                raise Rejected("native_security_rule_equivalence_unqualified", 423)
            choices = self.qualified_native_choices(
                intent, dest["platform"], cases, now,
            )
        else:
            choices = native_application_flow_choices(intent, observed["network"], policy)
        context_sha = digest({
            "assessment": retained["id"],
            "intent": current_intent["digest"],
            "destination": {
                k: dest[k] for k in
                ("tenant_id", "site_id", "endpoint_id", "native_scope",
                 "platform", "installed_tuple")
            },
            "profile": facts["profile"]["digest"],
            "policy": digest(policy),
        })
        expires = min(
            dest["capability_snapshot"]["expires_at"],
            qualification["verification"]["expires_at"],
            policy["expires_at"], now + 60,
        )
        return {
            "intent": intent, "destination": dest, "policy": policy,
            "assessment_id": retained["id"],
            "source_revision_id": current_intent["id"],
            "source_intent_sha256": current_intent["digest"],
            "destination_generation_id": candidate["generation_id"],
            "data": observed, "choices": choices,
            "context_sha256": context_sha, "expires_at": expires,
        }

    @staticmethod
    def qualified_native_choices(
        intent: dict[str, Any], platform: str,
        cases: list[dict[str, Any]], now: int,
    ) -> list[dict[str, Any]]:
        """Only independently E4-qualified existing NSX/Prism controls enter a dropdown."""
        case_map: dict[str, dict[str, Any]] = {}
        for case in cases:
            if (not isinstance(case, dict)
                    or set(case) != {"source_flow_id", "flow", "source_document", "document", "boundary"}
                    or not isinstance(case["document"], dict)):
                raise Rejected("native_security_case_incomplete", 423)
            flow_id = case["source_flow_id"]
            if not isinstance(flow_id, str) or flow_id in case_map:
                raise Rejected("native_security_case_ambiguous", 423)
            case_map[flow_id] = case
        choices = []
        used = set()
        for dependency in intent["dependencies"]:
            if dependency["kind"] != "communication":
                continue
            source = {k: dependency[k] for k in ("from", "to", "protocol", "port")}
            flow_id = digest(source)
            case = case_map.get(flow_id)
            if case is None and dependency["strength"] != "required":
                # Optional intent can be omitted, but only through the
                # independent reason-coded receiving-owner waiver workflow.
                choices.append({
                    "source_flow_id": flow_id, "source": source,
                    "required": False, "destination_firewall_rule_ids": [],
                    "destination_route_ids": [], "status": "held_optional",
                    "native_write_authorized": False,
                })
                continue
            if (case is None or case["flow"] != source
                    or case["document"].get("platform") != platform
                    or not isinstance(case["source_document"], dict)
                    or case["source_document"].get("platform")
                       not in {"vmware", "ahv", "openstack"}):
                raise Rejected("native_security_application_coverage_incomplete", 423)
            boundary = compare_policy_boundary(
                case["source_document"], case["document"], case["boundary"], now,
            )
            if boundary["status"] != "qualified":
                raise Rejected("native_security_" + boundary["reason"], 423)
            source_verdict = qualify_effective_security(
                case["source_document"], source, now,
            )
            if source_verdict["status"] != "qualified":
                raise Rejected("native_source_security_" + source_verdict["reason"], 423)
            verdict = qualify_effective_security(case["document"], source, now)
            if verdict["status"] != "qualified":
                raise Rejected("native_security_" + verdict["reason"], 423)
            used.add(flow_id)
            choices.append({
                "source_flow_id": flow_id,
                "source": source,
                "required": dependency["strength"] == "required",
                "destination_firewall_rule_ids": [verdict["effective_rule_native_ref"]],
                "destination_route_ids": ["path:" + verdict["path_sha256"]],
                "status": "choices_observed",
                "native_write_authorized": False,
            })
        if set(case_map) != used:
            raise Rejected("native_security_unrelated_case", 423)
        return choices

    def _read_saved(self, actor: Actor, site: str, assessment_id: str) -> dict[str, Any] | None:
        with self.planning.database.transaction() as tx:
            row = tx.one(
                "SELECT revision,context_sha256,payload,updated_at,reviewed_by_actor "
                "FROM app.planning_application_flow_reviews WHERE " + SCOPE_SQL,
                (*self.scope(actor, site), identifier(assessment_id)),
            )
        return row

    @staticmethod
    def native_control_digest(current: dict[str, Any], selections: list[dict[str, Any]]) -> str:
        """Hash selected native semantics, not volatile observer timestamps.

        This is only a drift detector. Positive equivalence still requires
        current independent E4 tests and the signed admission receipt.
        """
        net = current["data"]["network"]
        choices = {row["source_flow_id"]: row for row in current["choices"]}
        controls = []
        if current["destination"].get("platform") in {"vmware", "ahv"}:
            cases = {
                item["source_flow_id"]: item["document"]
                for item in current["data"]["effective_security_cases"]
            }
            for selection in selections:
                flow_id = selection["source_flow_id"]
                if flow_id not in choices or flow_id not in cases:
                    raise Rejected("unapproved_application_flow")
                option = choices[flow_id]
                if (selection["rule_native_ref"] not in option["destination_firewall_rule_ids"]
                        or selection["route_native_ref"] not in option["destination_route_ids"]):
                    raise Rejected("application_flow_native_control_changed", 423)
                document = cases[flow_id]
                controls.append({
                    "flow_id": flow_id,
                    "groups": document["groups"],
                    "services": document["services"],
                    "rules": document["rules"],
                    "paths": document["paths"],
                    "path_set_sha256": document["path_set_sha256"],
                    "workloads": document["workloads"],
                    "boundary_scope": document["boundary_scope"],
                    "default_action": document["default_action"],
                    "topology_sha256": document["topology_sha256"],
                })
            return digest(sorted(controls, key=lambda row: row["flow_id"]))
        for selection in selections:
            source_id = selection.get("source_flow_id")
            option = choices.get(source_id)
            if option is None:
                raise Rejected("unapproved_application_flow")
            flows = option["source"]
            rule = [r for r in net.get("firewall_rules", []) if isinstance(r, dict)
                    and r.get("native_ref") == selection.get("rule_native_ref")
                    and all(r.get(k) == flows[k] for k in
                            ("from", "to", "protocol", "port"))]
            route = [r for r in net.get("topology", {}).get("routes", [])
                     if isinstance(r, dict)
                     and r.get("native_ref") == selection.get("route_native_ref")
                     and r.get("from") == flows["from"] and r.get("to") == flows["to"]]
            if len(rule) != 1 or len(route) != 1:
                raise Rejected("application_flow_native_control_changed", 423)
            transient = {"observed_at", "expires_at", "last_seen_at", "sequence"}
            controls.append({
                "flow_id": source_id,
                "firewall": {k: v for k, v in rule[0].items() if k not in transient},
                "route": {k: v for k, v in route[0].items() if k not in transient},
            })
        return digest(sorted(controls, key=lambda row: row["flow_id"]))

    @staticmethod
    def evaluate(
        current: dict[str, Any], selections: Any, now: int,
        omissions: Any = None,
    ) -> list[str]:
        choices, data = current["choices"], deepcopy(current["data"])
        if not isinstance(selections, list) or len(selections) > 512:
            raise Rejected("invalid_application_flow_selection")
        if omissions is None:
            omissions = []
        if not isinstance(omissions, list) or len(omissions) > 512:
            raise Rejected("invalid_application_flow_omission")
        allowed = {row["source_flow_id"]: row for row in choices}
        if len(allowed) != len(choices):
            raise Rejected("ambiguous_application_flow_intent")
        seen: set[str] = set()
        bound: dict[str, Any] = {}
        network = data["network"]
        vendor = current["destination"].get("platform") in {"vmware", "ahv"}
        observer = network.get("observer_principal")
        writer = network.get("writer_principal")
        if current["expires_at"] <= now:
            return ["independent_native_flow_observer_required"]
        if not vendor and (
            not isinstance(observer, str) or not observer
            or not isinstance(writer, str) or not writer or observer == writer
        ):
            return ["independent_native_flow_observer_required"]
        cases = {
            item["source_flow_id"]: item["document"]
            for item in data.get("effective_security_cases", [])
        } if vendor else {}
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
                "observer_principal": (
                    cases[flow_id]["observer_principal"] if vendor else observer
                ),
                "observed_at": current["destination"]["capability_snapshot"]["observed_at"],
                "expires_at": current["expires_at"],
                "policy_sha256": digest(current["policy"]),
                "topology_sha256": network["topology_sha256"],
            }
        missing = [row["source_flow_id"] for row in choices if row["required"]
                   and row["source_flow_id"] not in seen]
        if missing:
            return ["application_flow_required_selection_missing"]
        # Optional omissions are typed owner requests, never self-approval.
        # A separate, current E4 Assurance decision must approve exactly
        # these omitted source dependency IDs before native admission.
        reason_codes = {
            "retired_dependency", "not_required_at_destination",
            "replaced_by_native_service", "accepted_service_limitation",
        }
        requested: set[str] = set()
        for omission in omissions:
            if (
                not isinstance(omission, dict)
                or set(omission) != {"source_flow_id", "reason_code"}
                or not isinstance(omission["source_flow_id"], str)
                or omission["source_flow_id"] in requested
                or omission["source_flow_id"] in seen
                or omission["reason_code"] not in reason_codes
                or omission["source_flow_id"] not in allowed
                or allowed[omission["source_flow_id"]]["required"]
            ):
                raise Rejected("invalid_application_flow_omission")
            requested.add(omission["source_flow_id"])
        missing_optional = {
            row["source_flow_id"] for row in choices
            if not row["required"] and row["source_flow_id"] not in seen
        }
        if not missing_optional <= requested:
            return ["application_flow_optional_omission_declaration_required"]
        omission_hold = bool(requested)
        # Application-owner selection is an overlay for assessment, never an
        # alteration to the native observed snapshot's asserted reality.
        network["application_flow_selections"] = bound
        check_data = dict(data)
        check_data["network"] = network
        try:
            checks = []
            if vendor:
                for selection in selections:
                    source_id = selection["source_flow_id"]
                    source = allowed[source_id]["source"]
                    certificate = cases.get(source_id)
                    if not isinstance(certificate, dict):
                        return ["native_security_case_missing"]
                    verdict = qualify_effective_security(certificate, source, now)
                    if (verdict["status"] != "qualified"
                            or verdict["effective_rule_native_ref"] != selection["rule_native_ref"]
                            or "path:" + verdict["path_sha256"] != selection["route_native_ref"]):
                        return ["native_security_effective_policy_changed"]
            else:
                checks = network_checks(current["intent"], check_data, current["policy"], now)
            checks += isolation_checks(
                current["intent"], current["destination"], check_data,
                current["policy"], now,
            )
        except (KeyError, ValueError, TypeError, IndexError):
            return ["application_flow_independent_evidence_incomplete"]
        holds = {
            reason for _, status, reason, mandatory in checks
            if mandatory and status != "eligible"
        }
        if omission_hold:
            holds.add("application_flow_optional_omission_approval_required")
        return sorted(holds)

    def read(self, actor: Actor, site: str, delegation: str) -> dict[str, Any]:
        current = self.current(actor, site, delegation)
        saved = self._read_saved(actor, site, current["assessment_id"])
        changed = saved is not None and saved["context_sha256"] != current["context_sha256"]
        selections = saved["payload"]["selections"] if saved and not changed else []
        omissions = saved["payload"].get("omissions", []) if saved and not changed else []
        try:
            holds = self.evaluate(current, selections, self.planning.clock(), omissions)
        except (Rejected, KeyError, TypeError, ValueError):
            holds = ["application_flow_native_control_changed"]
            changed = True
        if saved and not changed:
            try:
                if saved["payload"].get("native_controls_sha256") != self.native_control_digest(current, selections):
                    changed = True
                    holds = ["application_flow_native_control_changed", *holds]
            except (Rejected, KeyError, TypeError, ValueError):
                changed = True
                holds = ["application_flow_native_control_changed", *holds]
        if changed:
            # Never offer an old native rule/route as a preselected default
            # after a scope, content or independent evidence change.
            selections = []
            omissions = []
            holds = ["application_flow_evidence_changed", *holds]
        return {
            "context_sha256": current["context_sha256"],
            "revision": saved["revision"] if saved else 0,
            "expires_at": current["expires_at"],
            "choices": current["choices"],
            "selections": selections,
            "omissions": omissions,
            "holds": list(dict.fromkeys(holds)),
            "status": ("invalidated" if changed else
                       "held" if holds else "eligible"),
            "native_write_authorized": False,
        }

    def save(
        self, actor: Actor, site: str, delegation: str, body: dict[str, Any], key: str
    ) -> dict[str, Any]:
        shape(body, {"site_id", "revision", "context_sha256", "selections", "omissions"})
        if body["site_id"] != site:
            raise Rejected("application_flow_site_mismatch", 403)
        revision = integer(body["revision"], 0, 1000000)
        identifier(key)
        current = self.current(actor, site, delegation)
        if body["context_sha256"] != current["context_sha256"]:
            raise Rejected("application_flow_evidence_changed", 412)
        holds = self.evaluate(
            current, body["selections"], self.planning.clock(), body["omissions"],
        )
        canonical(body)
        if len(canonical(body).encode()) > 32768:
            raise Rejected("application_flow_payload_bound", 413)
        fingerprint = digest({
            "operation": "migration_flow_save", "scope": self.scope(actor, site),
            "assessment_id": current["assessment_id"], "body": body,
        })
        with self.planning.database.transaction() as tx:
            tx.execute("SELECT pg_advisory_xact_lock(7504001)")
            prior = self.planning.retry(tx, actor, key, fingerprint)
            if prior:
                return prior
            old = tx.one(
                "SELECT revision FROM app.planning_application_flow_reviews "
                "WHERE " + SCOPE_SQL,
                (*self.scope(actor, site), current["assessment_id"]),
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
                "(tenant,application,environment,site,assessment_id,reviewed_by_actor,"
                "revision,context_sha256,payload,updated_at) "
                "VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s) "
                "ON CONFLICT (tenant,application,environment,site,assessment_id) "
                "DO UPDATE SET revision=excluded.revision,"
                "reviewed_by_actor=excluded.reviewed_by_actor,"
                "context_sha256=excluded.context_sha256,"
                "payload=excluded.payload,updated_at=excluded.updated_at",
                (*self.scope(actor, site), current["assessment_id"], actor.actor,
                 revision + 1, current["context_sha256"],
                 canonical({"selections": body["selections"],
                            "omissions": body["omissions"], "holds": holds,
                            "assessment_id": current["assessment_id"],
                            "native_controls_sha256": self.native_control_digest(
                                current, body["selections"]),
                            "source_revision_id": current["source_revision_id"],
                            "source_intent_sha256": current["source_intent_sha256"],
                            "destination_generation_id": current["destination_generation_id"],
                            "destination_platform": current["destination"]["platform"],
                            "expires_at": current["expires_at"]}), self.planning.clock()),
            )
            tx.execute(
                "INSERT INTO app.planning_commands "
                "(tenant,actor,command_key,fingerprint,response,created_at) "
                "VALUES(%s,%s,%s,%s,%s::jsonb,%s)",
                (actor.tenant, actor.actor, key, fingerprint,
                 canonical(outcome), self.planning.clock()),
            )
        return outcome

    def _latest_assessment_id(self, actor: Actor, site: str) -> str:
        with self.planning.database.transaction() as tx:
            row = tx.one(
                "SELECT id FROM app.planning_records WHERE tenant=%s AND "
                "application=%s AND environment=%s AND "
                "kind='assessment' AND payload->>'action'='application.migrate' "
                "AND payload->'candidates' @> %s::jsonb "
                "ORDER BY created_at DESC,id DESC LIMIT 1",
                (*self.scope(actor, site)[:3], canonical([{"site_id": site}])),
            )
        if row is None:
            raise Rejected("application_migration_assessment_required", 423)
        return str(row["id"])

    def require(self, actor: Actor, site: str, binding: dict[str, Any]) -> None:
        """Execution-side fail-closed gate; no owner delegation is minted here."""
        saved = self._read_saved(actor, site, self._latest_assessment_id(actor, site))
        if saved is None or saved["payload"].get("selections") is None:
            raise Rejected("approved_application_flow_selection_required", 423)
        # Owner choices outlive native telemetry. A reviewed selection is not
        # execution evidence: the independent service-only verifier below
        # must obtain fresh current source identity and runtime probes.
        remaining = set(saved["payload"].get("holds", []))
        remaining.discard("application_flow_optional_omission_approval_required")
        if remaining:
            raise Rejected("application_flow_not_eligible", 423)
        # A more recent application migration assessment for this actor/site
        # supersedes the earlier reviewed source and destination flow choice,
        # even before its normal short expiry has elapsed.
        with self.planning.database.transaction() as tx:
            latest = tx.one(
                "SELECT id FROM app.planning_records WHERE tenant=%s AND "
                "application=%s AND environment=%s AND "
                "kind='assessment' AND payload->>'action'='application.migrate' "
                "AND payload->'candidates' @> %s::jsonb "
                "ORDER BY created_at DESC,id DESC LIMIT 1",
                (*self.scope(actor, site)[:3],
                 canonical([{"site_id": site}])),
            )
        if (
            latest is None
            or str(latest["id"]) != saved["payload"].get("assessment_id")
        ):
            raise Rejected("application_flow_assessment_superseded", 423)
        if self.execution_proof is None:
            raise Rejected("independent_application_flow_e4_required", 423)
        self.execution_proof(actor, site, saved, self.planning.clock(), binding)
        # A new assessment published while the independent owner calls were
        # in flight must not inherit the result of this older review.
        if self._latest_assessment_id(actor, site) != saved["payload"]["assessment_id"]:
            raise Rejected("application_flow_assessment_superseded", 423)
