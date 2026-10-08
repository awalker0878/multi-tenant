"""Independent native API observations for exact commissioned acceptance cases.

Every check reads its enrolled service directly. Protected manifests identify the
native subject and expected configuration/data; browser input cannot supply an
endpoint, credential, predicate or a passed outcome. Raw service data is not returned.
"""

import hashlib
import re
from collections.abc import Callable
from pathlib import Path
from typing import Any

from lifecycle_worker.application.api_plan import shape
from lifecycle_worker.application.native import NativeHeld, decode, digest, identity, sha256
from lifecycle_worker.infrastructure.migration_bootstrap import endpoint
from lifecycle_worker.infrastructure.native_files import protected_read
from lifecycle_worker.infrastructure.native_json import NativeJson


def pointer(document: Any, path: str) -> Any:
    if not isinstance(path, str) or not path.startswith("/") or len(path) > 1024:
        raise NativeHeld("probe_pointer_invalid")
    value = document
    for key in path[1:].split("/"):
        if re.search(r"~(?![01])", key):
            raise NativeHeld("probe_pointer_invalid")
        key = key.replace("~1", "/").replace("~0", "~")
        if isinstance(value, dict) and key in value:
            value = value[key]
        elif (
            isinstance(value, list)
            and re.fullmatch(r"0|[1-9][0-9]{0,4}", key)
            and int(key) < len(value)
        ):
            value = value[int(key)]
        else:
            raise NativeHeld("probe_field_missing")
    return value


def matches(document: Any, predicate: dict[str, Any], now: int) -> bool:
    shape(predicate, {"pointer", "operator", "value"})
    value = pointer(document, predicate["pointer"])
    expected, operator = predicate["value"], predicate["operator"]
    if operator == "equals":
        return digest(value) == digest(expected)
    if operator == "maximum_age_seconds":
        return (
            type(value) is int
            and type(expected) is int
            and 0 <= expected <= 86400
            and 0 <= now - value <= expected
        )
    if operator == "at_most":
        return (
            type(value) in {int, float}
            and type(expected) in {int, float}
            and 0 <= value <= expected
        )
    raise NativeHeld("probe_operator_unsupported")


def fresh_measurement(predicates: list[dict[str, Any]], pointer: str | None = None) -> bool:
    """A new GET cannot make an old health, restore or traffic result current."""
    return any(
        p.get("operator") == "maximum_age_seconds"
        and type(p.get("value")) is int
        and 0 <= p["value"] <= 300
        and (pointer is None or p.get("pointer") == pointer)
        for p in predicates
    )


class ProbeJson(NativeJson):
    def __init__(self, connection: dict[str, Any]) -> None:
        shape(
            connection,
            {
                "endpoint",
                "header",
                "prefix",
                "reader_principal",
                "writer_principal",
                "identity_path",
                "identity_pointer",
            },
        )
        if (
            connection["header"]
            not in {
                "Authorization",
                "X-Auth-Token",
                "X-Ntnx-Api-Key",
                "vmware-api-session-id",
                "Authtoken",
                "X-Api-Key",
            }
            or connection["prefix"] not in {"", "Bearer ", "Basic "}
            or not isinstance(connection["reader_principal"], str)
            or not connection["reader_principal"]
            or connection["reader_principal"] == connection["writer_principal"]
        ):
            raise NativeHeld("probe_independent_identity_required")
        super().__init__(endpoint(connection["endpoint"]), "X-Auth-Token")
        self.header, self.prefix, self.configuration = (
            connection["header"],
            connection["prefix"],
            connection,
        )

        self.expected_token_sha256 = hashlib.sha256(self.credential().encode()).hexdigest()

    def credential(self) -> str:
        return str(self.prefix) + super().credential()

    def verify(self, current: Callable[[], None]) -> None:
        row = self.request("GET", self.configuration["identity_path"], current)
        if (
            pointer(row, self.configuration["identity_pointer"])
            != self.configuration["reader_principal"]
        ):
            raise NativeHeld("probe_native_principal_changed")


class NativeEvidenceProbes:
    def __init__(self, registry: Path, observer_id: str, clock: Callable[[], int]) -> None:
        self.registry, self.observer_id, self.clock = registry, identity(observer_id), clock

    def observe(self, tenant: str, caller: str, body: dict[str, Any]) -> dict[str, Any]:
        shape(body, {"plan", "binding", "phase"})
        plan, binding, phase = body["plan"], body["binding"], body["phase"]
        if (
            phase not in {"before", "after"}
            or plan["scope"]["tenant_id"] != tenant
            or self.observer_id in {plan["actor_id"], plan["requester_id"], plan["executor_id"]}
            or binding["plan_sha256"] != digest(plan)
            or binding["executor_id"] != plan["executor_id"]
            or binding["epoch"] != plan["epoch"]
            or binding["intent_digest"] != plan["intents"][binding["stage"]]
        ):
            raise NativeHeld("probe_scope_changed")
        for key in ("job_id", "operation_id", "attempt_id", "grant_id"):
            identity(binding[key])
        raw = protected_read(self.registry, 1048576)
        registry = decode(raw)
        shape(registry, {"schema_version", "assignments"})
        if registry["schema_version"] != 1 or not isinstance(registry["assignments"], list):
            raise NativeHeld("probe_registry_invalid")
        selected = [
            r
            for r in registry["assignments"]
            if r.get("plan_sha256") == digest(plan)
            and r.get("caller_id") == caller
            and r.get("stage") == binding["stage"]
            and r.get("phase") == phase
        ]
        if len(selected) != 1:
            raise NativeHeld("probe_manifest_not_commissioned")
        manifest = selected[0]
        shape(manifest, {"plan_sha256", "caller_id", "stage", "phase", "expires_at", "cases"})
        if type(manifest["expires_at"]) is not int or manifest["expires_at"] <= self.clock():
            raise NativeHeld("probe_manifest_expired")
        cases = manifest["cases"]
        if not isinstance(cases, list) or not 1 <= len(cases) <= 512:
            raise NativeHeld("probe_manifest_bound")

        def current() -> None:
            if (
                protected_read(self.registry, 1048576) != raw
                or self.clock() >= manifest["expires_at"]
            ):
                raise NativeHeld("probe_manifest_changed")

        records, seen = [], set()
        for case in cases:
            shape(
                case,
                {
                    "case",
                    "connection",
                    "path",
                    "subject",
                    "predicates",
                    "requirement_sha256",
                    "policy_results",
                },
            )
            name = case["case"]
            if (
                not isinstance(name, str)
                or not re.fullmatch(r"[A-Za-z0-9_-]{1,100}", name)
                or name in seen
            ):
                raise NativeHeld("probe_case_ambiguous")
            seen.add(name)
            shape(case["subject"], {"pointer", "operator", "value"})
            if case["subject"]["operator"] != "equals" or not case["subject"]["value"]:
                raise NativeHeld("probe_native_subject_required")
            predicates = case["predicates"]
            if not isinstance(predicates, list) or not 1 <= len(predicates) <= 256:
                raise NativeHeld("probe_assertions_required")
            if (
                name.startswith(("service_", "dataset_", "security_rule_"))
                or name
                in {
                    "application_health",
                    "guest_ready",
                    "guest_boot",
                    "guest_drivers",
                    "guest_storage",
                    "guest_network",
                    "guest_identity",
                    "source_application_healthy",
                    "backup_restore",
                    "policy_paths",
                    "required_services",
                    "one_writer",
                    "no_target_divergence",
                    "final_integrity",
                    "rehearsal_integrity",
                    "recovered_integrity",
                    "source_return_integrity",
                }
            ) and not fresh_measurement(predicates):
                raise NativeHeld("probe_native_measurement_freshness_required")
            api = ProbeJson(case["connection"])
            current()
            api.verify(current)
            response = api.request("GET", case["path"], current)
            if not matches(response, case["subject"], self.clock()):
                raise NativeHeld("probe_native_subject_changed")
            if not all(matches(response, predicate, self.clock()) for predicate in predicates):
                raise NativeHeld("probe_native_outcome_failed")
            policy_results = case["policy_results"]
            if not isinstance(policy_results, dict):
                raise NativeHeld("probe_policy_results_invalid")
            # Every traffic expectation must also occur in the observed response.
            if name == "policy_paths":
                if not policy_results:
                    raise NativeHeld("probe_policy_measurement_required")
                for key, expectation in policy_results.items():
                    if expectation not in {"allow", "deny"} or not any(
                        p["operator"] == "equals"
                        and p["value"] == {"id": key, "outcome": expectation}
                        and fresh_measurement(
                            predicates, p["pointer"].rsplit("/", 1)[0] + "/observed_at"
                        )
                        for p in predicates
                    ):
                        raise NativeHeld("probe_policy_measurement_required")
            elif policy_results:
                raise NativeHeld("probe_policy_results_unexpected")
            now = self.clock()
            record = {
                "case": name,
                "phase": phase,
                "binding_sha256": digest(binding),
                "intent_digest": binding["intent_digest"],
                "observer_id": self.observer_id,
                "observed_at": now,
                "expires_at": min(now + 30, manifest["expires_at"]),
                "outcome": "passed",
                "evidence_sha256": digest({"probe": case, "response": response}),
                "policy_results": policy_results,
            }
            requirement = case["requirement_sha256"]
            if requirement is not None:
                if not sha256(requirement):
                    raise NativeHeld("probe_requirement_invalid")
                record["requirement_sha256"] = requirement
            records.append(record)
        current()
        # Slow multi-service observations are repeated, never restamped as fresh.
        if any(self.clock() >= r["expires_at"] for r in records):
            raise NativeHeld("probe_batch_expired")
        return {"records": records}
