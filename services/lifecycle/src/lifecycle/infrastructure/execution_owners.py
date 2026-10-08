"""Bounded TLS-only owner clients and independently mounted E2 campaign authority."""

import hmac
import http.client
import json
import os
import re
import ssl
import time
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from lifecycle.domain.admission import digest
from lifecycle.domain.execution import Rejected, decode, identity
from lifecycle.infrastructure.foundation import mounted_secret


def request(
    owner: str,
    method: str,
    path: str,
    body: dict[str, Any] | None = None,
    delegation: str | None = None,
) -> dict[str, Any]:
    try:
        url = urlsplit(os.environ[owner + "_URL"])
        ca = os.environ[owner + "_CA_FILE"]
        if (
            url.scheme != "https"
            or not url.hostname
            or url.path
            or url.username
            or url.password
            or url.query
            or url.fragment
            or not os.path.isabs(ca)
        ):
            raise ValueError
        credential = mounted_secret("LIFECYCLE_" + owner + "_CREDENTIAL_FILE")
        headers = {
            "Authorization": "Bearer " + credential,
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Accept-Encoding": "identity",
        }
        if delegation:
            headers["X-Actor-Delegation"] = delegation
        connection = http.client.HTTPSConnection(
            url.hostname, url.port or 443, timeout=5, context=ssl.create_default_context(cafile=ca)
        )
        try:
            connection.request(method, path, None if body is None else json.dumps(body), headers)
            response = connection.getresponse()
            raw = response.read(524289)
            if response.status in {401, 403, 404, 409, 423}:
                raise Rejected("owner_denied", response.status)
            if (
                response.status not in {200, 201}
                or len(raw) > 524288
                or response.getheader("Content-Encoding", "identity") != "identity"
            ):
                raise ValueError
            return decode(raw)
        finally:
            connection.close()
    except Rejected:
        raise
    except (KeyError, ValueError, TypeError, OSError, http.client.HTTPException):
        raise Rejected("owner_unavailable", 503) from None


class ExecutionOwners:
    def caller(self, credential: str, audience: str) -> None:
        if audience not in {"console", "simulator", "assurance"}:
            raise Rejected("invalid_workload", 401)
        try:
            expected = mounted_secret("LIFECYCLE_" + audience.upper() + "_CALLER_FILE")
            others = [
                mounted_secret("LIFECYCLE_" + name.upper() + "_CALLER_FILE")
                for name in ("console", "simulator", "assurance")
                if name != audience
            ]
            others.append(mounted_secret("LIFECYCLE_GOVERNANCE_CREDENTIAL_FILE"))
            if expected in others or not hmac.compare_digest(expected, credential):
                raise Rejected("invalid_workload", 401)
        except (KeyError, ValueError, OSError):
            raise Rejected("authority_unavailable", 503) from None

    def actor(self, delegation: str, tenant: str, action: str, scope: dict[str, Any]) -> str:
        if not re.fullmatch(r"[0-9a-f]{64}", delegation):
            raise Rejected("invalid_delegation", 403)
        scope = {k: scope[k] for k in ("site_id", "environment", "resource_id")}
        result = request(
            "GOVERNANCE",
            "POST",
            f"/v1/tenants/{tenant}/delegated-authorizations",
            {"action": action, "scope": scope},
            delegation,
        )
        expected = {
            "allowed": True,
            "audience": "lifecycle",
            "tenant_id": tenant,
            "action": action,
            "scope": scope,
            "authority_use": "request_bound",
            "delegating_service": "console",
        }
        if any(result.get(k) != v for k, v in expected.items()):
            raise Rejected("authority_mismatch", 403)
        now = time.time()
        if (
            not now
            < datetime.fromisoformat(result["expires_at"].replace("Z", "+00:00")).timestamp()
            <= now + 65
            or abs(
                now
                - datetime.fromisoformat(result["evaluated_at"].replace("Z", "+00:00")).timestamp()
            )
            > 5
        ):
            raise Rejected("authority_expired", 403)
        return identity(result["actor_id"])

    def plan(self, tenant: str, plan: str, revision: int) -> dict[str, Any]:
        return request(
            "PLANNING",
            "GET",
            f"/v1/tenants/{identity(tenant)}/execution-plans/{identity(plan)}/revisions/{revision}",
        )

    def custody(self) -> str:
        try:
            path = Path(os.environ["LIFECYCLE_CUSTODY_EPOCH_FILE"])
            if not path.is_absolute() or path.stat().st_size > 128:
                raise ValueError
            return identity(path.read_text().strip())
        except (KeyError, ValueError, OSError):
            raise Rejected("custody_unavailable", 423) from None

    def current(self, job: dict[str, Any]) -> dict[str, Any]:
        tenant, binding = job["tenant"], job["binding"]
        plan = self.plan(tenant, binding["plan_id"], binding["revision"])
        if (
            plan.get("invalidated") is not False
            or plan.get("content") != job["plan"]
            or plan.get("binding") != binding
        ):
            raise Rejected("plan_changed", 403)
        approval = request(
            "GOVERNANCE",
            "POST",
            f"/v1/tenants/{tenant}/execution-approval-checks",
            {
                "actor_id": job["actor"],
                "approval_id": job["approval_id"],
                "plan_id": binding["plan_id"],
                "plan_revision": binding["revision"],
                "plan_digest": binding["digest"],
            },
        )
        expected = {
            "allowed": True,
            "tenant_id": tenant,
            "actor_id": job["actor"],
            "approval_id": job["approval_id"],
            "plan_digest": binding["digest"],
            "authority_use": "simulation_boundary",
            "native_write_authorized": False,
        }
        if (
            any(approval.get(k) != v for k, v in expected.items())
            or not 0 <= int(time.time()) - approval.get("evaluated_at", 0) <= 5
        ):
            raise Rejected("approval_not_current", 403)
        if (
            job.get("admission", {}).get("executor_fingerprint", approval["executor_fingerprint"])
            != approval["executor_fingerprint"]
        ):
            raise Rejected("executor_authority_changed", 403)
        try:
            path = Path(os.environ["LIFECYCLE_SIMULATION_CAMPAIGNS_FILE"])
            if not path.is_absolute() or path.stat().st_size > 524288:
                raise ValueError
            registry = decode(path.read_bytes())
            if registry.get("schema_version") != 1:
                raise ValueError
            matches = [r for r in registry["records"] if r["campaign"]["id"] == job["campaign_id"]]
            if len(matches) != 1:
                raise ValueError
            current = matches[0]
            if (
                current.get("simulation") is not True
                or current["campaign"]["endpoint_allowlist"] != [os.environ["SIMULATOR_URL"]]
                or current["campaign"].get("custody_epoch") != self.custody()
            ):
                raise ValueError
            source = os.environ["LIFECYCLE_SOURCE_REVISION"]
            if (
                not re.fullmatch(r"[0-9a-f]{40}", source)
                or job.get("admission", {}).get("source_revision", source) != source
            ):
                raise Rejected("execution_source_changed", 423)
            current.update(
                source_revision=source,
                approval=approval["approval"] | {"scope": job["plan"]["scope"]},
                entitled=True,
                actor_id=job["actor"],
                evaluated_at=int(time.time()),
                executor_fingerprint=approval["executor_fingerprint"],
            )
            return dict(current)
        except (KeyError, ValueError, TypeError, OSError):
            raise Rejected("campaign_unavailable", 403) from None


class SimulatedEffects:
    def execute(self, grant: dict[str, Any]) -> dict[str, Any]:
        return request("SIMULATOR", "POST", "/v1/effects", grant)

    def reconcile(self, operation: dict[str, Any]) -> dict[str, Any]:
        return request("SIMULATOR", "POST", "/v1/reconciliations", operation)


class EvidenceCustody:
    def finalize(self, job: dict[str, Any], observations: list[dict[str, Any]]) -> dict[str, Any]:
        import base64

        source = job["admission"]["source_revision"]
        if not re.fullmatch(r"[0-9a-f]{40}", source):
            raise Rejected("source_revision_required", 503)
        raw = json.dumps(
            observations, sort_keys=True, ensure_ascii=True, allow_nan=False, separators=(",", ":")
        ).encode()
        body = {
            "job_id": job["id"],
            "plan_digest": job["binding"]["digest"],
            "source_revision": source,
            "digest": digest(observations),
            "evidence_level": "E2",
            "content_base64": base64.b64encode(raw).decode(),
        }
        receipt = request(
            "ASSURANCE", "POST", f"/v1/tenants/{job['tenant']}/evidence-uploads", body
        )
        return request(
            "ASSURANCE",
            "POST",
            f"/v1/tenants/{job['tenant']}/evidence-uploads/{identity(receipt['id'])}/finalization",
            {},
        )


class AlertReceiver:
    def deliver(self, event: dict[str, Any]) -> str:
        result = request("ALERTS", "POST", "/v1/lifecycle-alerts", event)
        if result.get("event_id") != event["id"] or result.get("acknowledged") is not True:
            raise Rejected("alert_not_acknowledged", 503)
        return str(result["receipt_id"])
