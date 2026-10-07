"""Native owner composition. Every boundary reads live owners; no simulation grants.

The custody endpoint owns provider fencing/state, installed qualification and worker
placement. Governance owns human consent. Inventory owns confirmed facts. Planning
owns immutable bytes. A mounted assignment only selects those records.
"""

import hmac
import json
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from lifecycle.domain.admission import digest
from lifecycle.domain.campaign_plan import native_plan_record, plan_requirements
from lifecycle.domain.execution import Rejected, decode, identity
from lifecycle.domain.migration import current_profiles
from lifecycle.domain.native_workflow import (
    checksum,
    current_authority,
    exact,
    integer,
    observations,
    validate_plan,
)
from lifecycle.infrastructure.campaign_observers import protected
from lifecycle.infrastructure.native_effects import (
    NativeEffectConnection,
    NativeWorkerEndpoint,
    credential,
)


def endpoint(value: Any) -> NativeWorkerEndpoint:
    exact(value, {"origin", "address", "ca_file", "credential_file"})
    protected(value["ca_file"], 1048576)
    return NativeWorkerEndpoint(
        value["origin"], value["address"], Path(value["ca_file"]), Path(value["credential_file"])
    )


class NativeOwnerConfiguration:
    def __init__(self, path: Path, clock: Callable[[], int]) -> None:
        self.path, self.clock = path, clock

    def load(self) -> dict[str, Any]:
        try:
            value = decode(protected(str(self.path), 1048576))
            exact(value, {"schema_version", "expires_at", "owners", "assignments", "workers"})
            if type(value["schema_version"]) is not int or value["schema_version"] != 1:
                raise ValueError
            if integer(value["expires_at"]) <= self.clock():
                raise ValueError
            exact(value["owners"], {"planning", "governance", "inventory", "custody", "observer"})
            tokens = []
            for spec in value["owners"].values():
                tokens.append(credential(endpoint(spec).credential_file))
            workers = value["workers"]
            if not isinstance(workers, list) or not 1 <= len(workers) <= 256:
                raise ValueError
            worker_ids = set()
            for worker in workers:
                exact(worker, {"tenant_id", "executor_id", "endpoint", "caller_file"})
                identity(worker["tenant_id"])
                worker_key = identity(worker["executor_id"])
                if worker_key in worker_ids:
                    raise ValueError
                worker_ids.add(worker_key)
                tokens.extend(
                    [
                        credential(endpoint(worker["endpoint"]).credential_file),
                        credential(Path(worker["caller_file"])),
                    ]
                )
            if len(set(tokens)) != len(tokens):
                raise ValueError
            entries = value["assignments"]
            if not isinstance(entries, list) or not 1 <= len(entries) <= 256:
                raise ValueError
            keys = set()
            for entry in entries:
                exact(
                    entry,
                    {
                        "tenant_id",
                        "plan_id",
                        "plan_revision",
                        "plan_digest",
                        "approval_id",
                        "actor_id",
                        "executor_id",
                        "campaign_id",
                        "epoch",
                    },
                )
                for name in set(entry) - {"plan_revision", "plan_digest"}:
                    identity(entry[name])
                integer(entry["plan_revision"], 1)
                checksum(entry["plan_digest"])
                key = (
                    entry["tenant_id"],
                    entry["plan_id"],
                    entry["plan_revision"],
                    entry["approval_id"],
                )
                if key in keys or not any(
                    w["tenant_id"] == entry["tenant_id"]
                    and w["executor_id"] == entry["executor_id"]
                    for w in workers
                ):
                    raise ValueError
                keys.add(key)
            return value
        except Exception:
            raise Rejected("native_owner_configuration_held", 423) from None

    def authorize_worker(self, token: str) -> tuple[str, str]:
        config = self.load()
        matches = [
            w
            for w in config["workers"]
            if hmac.compare_digest(credential(Path(w["caller_file"])), token)
        ]
        if len(matches) != 1:
            raise Rejected("native_worker_denied", 401)
        return matches[0]["tenant_id"], matches[0]["executor_id"]

    def assignment(self, tenant: str, ref: dict[str, Any]) -> dict[str, Any]:
        value = self.load()
        matches = [
            e
            for e in value["assignments"]
            if e["tenant_id"] == tenant
            and all(
                e[k] == ref[k] for k in ("plan_id", "plan_revision", "plan_digest", "approval_id")
            )
        ]
        if len(matches) != 1:
            raise Rejected("native_assignment_not_current", 423)
        return dict(matches[0])


class NativeOwnerTransport:
    def __init__(self, configuration: NativeOwnerConfiguration) -> None:
        self.configuration = configuration

    def request(
        self, owner: str, method: str, path: str, body: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        connection = None
        try:
            initial = self.configuration.load()
            spec = endpoint(initial["owners"][owner])
            token = credential(spec.credential_file)
            connection = NativeEffectConnection(spec)
            connection.request(
                method,
                path,
                None if body is None else json.dumps(body),
                {
                    "Authorization": "Bearer " + token,
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                    "Accept-Encoding": "identity",
                },
            )
            response = connection.getresponse()
            if (
                response.status != 200
                or response.getheader("Content-Encoding", "identity") != "identity"
            ):
                raise ValueError
            if response.getheader("Content-Type", "").split(";")[0] != "application/json":
                raise ValueError
            data = bytearray()
            deadline = time.monotonic() + 5
            while True:
                if time.monotonic() >= deadline:
                    raise ValueError
                chunk = response.read1(min(65536, 1048577 - len(data)))
                if not chunk:
                    break
                data.extend(chunk)
                if len(data) > 1048576:
                    raise ValueError
            result = decode(bytes(data))
            if (
                digest(initial) != digest(self.configuration.load())
                or credential(spec.credential_file) != token
            ):
                raise ValueError
            return result
        except Exception:
            raise Rejected("native_owner_unavailable", 423) from None
        finally:
            if connection is not None:
                connection.close()


class NativeOwners:
    def __init__(
        self,
        configuration: NativeOwnerConfiguration,
        transport: NativeOwnerTransport,
        clock: Callable[[], int],
    ) -> None:
        self.configuration, self.transport, self.clock = configuration, transport, clock

    def plan(self, tenant: str, ref: dict[str, Any]) -> dict[str, Any]:
        return self.transport.request(
            "planning",
            "GET",
            f"/v1/tenants/{identity(tenant)}/execution-plans/{identity(ref['plan_id'])}"
            f"/revisions/{integer(ref['plan_revision'], 1)}",
        )

    def approval(self, assignment: dict[str, Any]) -> dict[str, Any]:
        result = self.transport.request(
            "governance",
            "POST",
            f"/v1/tenants/{assignment['tenant_id']}/native-approval-checks",
            {
                k: assignment[k]
                for k in ("actor_id", "approval_id", "plan_id", "plan_revision", "plan_digest")
            },
        )
        expected = {
            k: assignment[k] for k in ("tenant_id", "actor_id", "approval_id", "plan_digest")
        }
        expected.update(
            allowed=True, authority_use="native_approval", native_write_authorized=False
        )
        if any(digest(result.get(k)) != digest(v) for k, v in expected.items()):
            raise Rejected("native_approval_denied", 423)
        if not 0 <= self.clock() - integer(result.get("evaluated_at")) <= 5:
            raise Rejected("native_approval_stale", 423)
        checksum(result.get("executor_fingerprint"))
        identity(result.get("requester_id"))
        approved = result["approval"]
        if (
            approved.get("state") != "approved"
            or approved.get("revoked") is not False
            or approved.get("approver_grant_current") is not True
            or any(
                approved.get(k) != assignment[k]
                for k in ("plan_id", "plan_revision", "plan_digest")
            )
            or integer(approved.get("expires_at")) <= self.clock()
        ):
            raise Rejected("native_approval_denied", 423)
        identity(approved["approver_id"])
        return result

    def resolve(self, tenant: str, ref: dict[str, Any]) -> dict[str, Any]:
        config_digest = digest(self.configuration.load())
        assignment = self.configuration.assignment(tenant, ref)
        record = self.plan(tenant, ref)
        requirements = native_plan_record(record, ref, tenant)
        content, binding = record["content"], record["binding"]
        migrating = content["action"] == "application.migrate"
        key = "native_migration" if migrating else "native_provisioning"
        if ("native_migration" in content) == ("native_provisioning" in content):
            raise Rejected("one_native_composition_required", 423)
        native = content[key]
        exact(
            native,
            {
                "schema_version",
                "scope",
                "intents",
                "native",
                "source_job_id",
                "recipe_sha256",
                "recipe_id",
                "base_plan_id",
            }
            | ({"migration"} if migrating else {"purpose"}),
        )
        checksum(native["recipe_sha256"])
        identity(native["recipe_id"])
        identity(native["base_plan_id"])
        if (
            native["schema_version"] != 1
            or type(native["schema_version"]) is not int
            or binding.get("canonicalization") != "p05-json-v1"
            or content.get("holds") != []
            or content.get("lane") != "operational"
            or assignment["actor_id"] not in binding.get("executor_ids", [])
            or any(
                native["scope"].get(k) != binding.get(k)
                for k in ("tenant_id", "site_id", "environment", "resource_id")
            )
            or content["scope"].get("native_scope") != "project:" + native["scope"]["project_id"]
        ):
            raise Rejected("native_proposal_binding_changed", 423)
        if migrating:
            campaign = plan_requirements(record, ref, tenant)["requirements"]
            if any(campaign[k] != native["migration"][k] for k in ("mode", "method")):
                raise Rejected("native_proposal_binding_changed", 423)
        elif native["purpose"] not in {"provision", "retire"} or content["action"] != (
            "application." + native["purpose"]
        ):
            raise Rejected("native_proposal_binding_changed", 423)
        approval = self.approval(assignment)
        if (
            approval["requester_id"] != binding["requested_by"]
            or approval["approval"]["scope"] != requirements["scope"]
        ):
            raise Rejected("native_approval_scope_changed", 423)
        selected = native["native"]
        exact(
            selected,
            {
                "configuration",
                "tuple_digest",
                "source_revision",
                "ownership_digest",
                "custody_id",
                "custody_generation",
                "policy_cases",
            },
        )
        if digest(content["ownership"]) != selected["ownership_digest"] or any(
            content["native_api"].get(k) != selected[k]
            for k in ("custody_id", "custody_generation")
        ):
            raise Rejected("native_proposal_custody_changed", 423)
        plan = {
            "schema_version": 2 if migrating else 1,
            "scope": native["scope"],
            **{
                k: assignment[k]
                for k in (
                    "plan_id",
                    "plan_revision",
                    "plan_digest",
                    "approval_id",
                    "actor_id",
                    "executor_id",
                    "campaign_id",
                    "epoch",
                )
            },
            "requester_id": approval["requester_id"],
            "approver_id": approval["approval"]["approver_id"],
            "purpose": "migrate" if migrating else native["purpose"],
            "source_job_id": native["source_job_id"],
            **selected,
            "operation_plan_sha256": digest(native),
            "intents": native["intents"],
            "expires_at": min(
                integer(binding["valid_until"]),
                integer(content["valid_until"]),
                integer(content["input_fresh_until"]),
                integer(approval["approval"]["expires_at"]),
                self.configuration.load()["expires_at"],
            ),
        }
        if migrating:
            plan["migration"] = native["migration"]
        validate_plan(plan, self.clock())
        if config_digest != digest(self.configuration.load()):
            raise Rejected("native_owner_configuration_changed", 423)
        return plan

    def epoch(self) -> str:
        value = self.transport.request("custody", "GET", "/v1/native-custody/epoch")
        exact(value, {"epoch", "evaluated_at", "expires_at"})
        if (
            not 0 <= self.clock() - integer(value["evaluated_at"]) <= 5
            or integer(value["expires_at"]) <= self.clock()
        ):
            raise Rejected("native_custody_stale", 423)
        return identity(value["epoch"])

    def current(self, plan: dict[str, Any], binding: dict[str, Any]) -> dict[str, Any]:
        checked_at = self.clock()
        tenant, scope = plan["scope"]["tenant_id"], plan["scope"]
        if digest(self.resolve(tenant, plan)) != digest(plan):
            raise Rejected("native_plan_changed", 423)
        verified: dict[str, Any] = {"approval_current": True, "plan_current": True}
        if plan["purpose"] == "migrate":
            review = plan["migration"]["review"]
            inputs = self.transport.request(
                "inventory",
                "GET",
                f"/internal/tenants/{tenant}/migration-inputs/{scope['resource_id']}/"
                f"{scope['environment']}/{scope['site_id']}/{review['revision']}/{review['digest']}",
            )
            current_profiles(plan, inputs, self.clock())
            verified.update(
                migration_input=inputs,
                source_profile_current=True,
                target_profile_current=True,
                all_datasets_accounted=True,
            )
        receipt = self.transport.request(
            "custody", "POST", "/v1/native-custody/checks", {"plan": plan, "binding": binding}
        )
        if any(k in receipt and digest(receipt[k]) != digest(v) for k, v in verified.items()):
            raise Rejected("native_owner_held", 423)
        # Custody cannot substitute a different confirmed review or supply human consent.
        receipt = receipt | verified
        current_authority(plan, binding, receipt, self.clock())
        if self.epoch() != plan["epoch"] or self.clock() - checked_at > 5:
            raise Rejected("native_custody_changed", 423)
        return receipt

    def observe(
        self, plan: dict[str, Any], binding: dict[str, Any], phase: str
    ) -> list[dict[str, Any]]:
        result = self.transport.request(
            "observer",
            "POST",
            "/v1/native-observations",
            {"plan": plan, "binding": binding, "phase": phase},
        )
        exact(result, {"records"})
        records: list[dict[str, Any]] = result["records"]
        observations(plan, binding, phase, records, self.clock())
        return records
