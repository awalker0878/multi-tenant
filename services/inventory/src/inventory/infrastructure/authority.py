"Current Governance delegation, separate Console credential and enrolled worker trust."

import hashlib
import hmac
import http.client
import json
import os
import re
import ssl
import time
from datetime import datetime
from urllib.parse import urlsplit

from inventory.application.ports import Policies
from inventory.domain.discovery import Actor, EnrollmentPolicy, Rejected, Worker, identifier
from inventory.infrastructure.foundation import mounted_secret


class GovernanceAuthority:
    def __init__(self, policies: Policies) -> None:
        self.policies = policies

    def actor(
        self, credential: str, delegation: str, tenant: str, action: str, site: str | None
    ) -> Actor:
        try:
            incoming = mounted_secret("INVENTORY_CONSOLE_CREDENTIAL_FILE")
            outgoing = mounted_secret("INVENTORY_GOVERNANCE_CREDENTIAL_FILE")
            if incoming == outgoing or not hmac.compare_digest(incoming, credential):
                raise Rejected("invalid_workload", 401)
            if not re.fullmatch(r"[0-9a-f]{64}", delegation):
                raise Rejected("access_denied", 403)
            identifier(tenant)
            if site is not None:
                identifier(site)
            scope = {"site_id": site, "environment": None, "resource_id": None}
            u = urlsplit(os.environ["GOVERNANCE_URL"])
            if (
                u.scheme != "https"
                or not u.hostname
                or u.username
                or u.password
                or u.query
                or u.fragment
                or u.path
            ):
                raise ValueError("Invalid Governance origin")
            ca = os.environ["GOVERNANCE_CA_FILE"]
            if not os.path.isabs(ca):
                raise ValueError("Invalid CA")
            connection = http.client.HTTPSConnection(
                u.hostname, u.port or 443, timeout=4, context=ssl.create_default_context(cafile=ca)
            )
            try:
                connection.request(
                    "POST",
                    f"/v1/tenants/{tenant}/delegated-authorizations",
                    json.dumps({"action": action, "scope": scope}),
                    {
                        "Authorization": "Bearer " + outgoing,
                        "X-Actor-Delegation": delegation,
                        "Content-Type": "application/json",
                        "Accept": "application/json",
                        "Accept-Encoding": "identity",
                    },
                )
                response = connection.getresponse()
                if response.status in {401, 403, 404}:
                    raise Rejected("access_denied", 403)
                raw = response.read(16385)
                if (
                    response.status != 200
                    or len(raw) > 16384
                    or response.getheader("Content-Encoding", "identity") != "identity"
                ):
                    raise ValueError("Invalid authority response")
                body = json.loads(raw)
            finally:
                connection.close()
            if (
                body.get("allowed"),
                body.get("audience"),
                body.get("delegating_service"),
                body.get("authority_use"),
                body.get("tenant_id"),
                body.get("action"),
                body.get("scope"),
            ) != (True, "inventory", "console", "request_bound", tenant, action, scope):
                raise ValueError("Invalid authority scope")
            now = time.time()
            expiry = datetime.fromisoformat(body["expires_at"].replace("Z", "+00:00")).timestamp()
            evaluated = datetime.fromisoformat(
                body["evaluated_at"].replace("Z", "+00:00")
            ).timestamp()
            if not now < expiry <= now + 65 or abs(now - evaluated) > 5:
                raise ValueError("Stale authority")
            return Actor(
                tenant,
                identifier(body["actor_id"]),
                identifier(body["delegation_id"]),
                action,
                site,
            )
        except Rejected:
            raise
        except (KeyError, TypeError, ValueError, OSError, http.client.HTTPException):
            raise Rejected("authority_unavailable", 503) from None

    def worker(self, credential: str) -> Worker:
        fingerprint = hashlib.sha256(credential.encode()).hexdigest()
        ids = {
            p.worker
            for p in self.policies.load().values()
            if hmac.compare_digest(p.worker_fingerprint, fingerprint)
        }
        if len(ids) != 1:
            raise Rejected("worker_denied", 403)
        return Worker(ids.pop(), fingerprint)

    def collection(self, policy: EnrollmentPolicy) -> None:
        try:
            u = urlsplit(os.environ["GOVERNANCE_URL"])
            if (
                u.scheme != "https"
                or not u.hostname
                or u.username
                or u.password
                or u.query
                or u.fragment
                or u.path
            ):
                raise ValueError("Invalid Governance origin")
            ca = os.environ["GOVERNANCE_CA_FILE"]
            if not os.path.isabs(ca):
                raise ValueError("Invalid CA")
            connection = http.client.HTTPSConnection(
                u.hostname, u.port or 443, timeout=4, context=ssl.create_default_context(cafile=ca)
            )
            expected = {
                "owner_id": policy.owner,
                "site_id": policy.site,
                "policy_digest": policy.policy_digest,
            }
            try:
                connection.request(
                    "POST",
                    f"/v1/tenants/{policy.tenant}/inventory-collection-checks",
                    json.dumps(expected),
                    {
                        "Authorization": "Bearer "
                        + mounted_secret("INVENTORY_GOVERNANCE_CREDENTIAL_FILE"),
                        "Content-Type": "application/json",
                        "Accept-Encoding": "identity",
                    },
                )
                response = connection.getresponse()
                raw = response.read(16385)
                if (
                    response.status != 200
                    or len(raw) > 16384
                    or response.getheader("Content-Encoding", "identity") != "identity"
                ):
                    raise ValueError("Collection admission unavailable")
                body = json.loads(raw)
            finally:
                connection.close()
            if (
                body.get("allowed") is not True
                or body.get("native_write_authorized") is not False
                or body.get("tenant_id") != policy.tenant
                or any(body.get(k) != v for k, v in expected.items())
            ):
                raise ValueError("Invalid admission response")
            evaluated = datetime.fromisoformat(
                body["evaluated_at"].replace("Z", "+00:00")
            ).timestamp()
            if abs(time.time() - evaluated) > 5:
                raise ValueError("Stale admission")
        except (KeyError, TypeError, ValueError, OSError, http.client.HTTPException):
            raise Rejected("collection_authority_unavailable", 503) from None
