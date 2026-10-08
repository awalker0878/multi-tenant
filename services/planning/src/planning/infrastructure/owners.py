"""Verified TLS owner reads, current delegated authority, and independently mounted policy."""

import hashlib
import hmac
import http.client
import json
import os
import re
import ssl
import time
from datetime import datetime
from importlib.resources import files
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from jsonschema import Draft202012Validator, FormatChecker

from planning.domain.model import Actor, Rejected, decode, identifier, profile
from planning.infrastructure.foundation import mounted_secret


def request(
    owner: str,
    method: str,
    path: str,
    body: dict[str, Any] | None = None,
    delegation: str | None = None,
    action: str | None = None,
    schema_name: str | None = None,
) -> dict[str, Any]:
    try:
        u = urlsplit(os.environ[owner + "_URL"])
        ca = os.environ[owner + "_CA_FILE"]
        if (
            u.scheme != "https"
            or not u.hostname
            or u.path
            or u.username
            or u.password
            or u.query
            or u.fragment
            or not os.path.isabs(ca)
        ):
            raise ValueError
        token = mounted_secret("PLANNING_" + owner + "_CREDENTIAL_FILE")
        headers = {
            "Authorization": "Bearer " + token,
            "Accept": "application/json",
            "Accept-Encoding": "identity",
            "Content-Type": "application/json",
        }
        if delegation:
            headers["X-Actor-Delegation"] = delegation
        if action:
            headers["X-Planning-Action"] = action
        connection = http.client.HTTPSConnection(
            u.hostname, u.port or 443, timeout=5, context=ssl.create_default_context(cafile=ca)
        )
        try:
            connection.request(method, path, None if body is None else json.dumps(body), headers)
            response = connection.getresponse()
            raw = response.read(524289)
            if response.status in {401, 403, 404}:
                raise Rejected("source_access_denied", 403)
            if (
                response.status != 200
                or len(raw) > 524288
                or response.getheader("Content-Encoding", "identity") != "identity"
            ):
                raise ValueError
            result = decode(raw)
            if not isinstance(result, dict):
                raise ValueError
            if owner in {"CATALOGUE", "INVENTORY", "ASSURANCE"}:
                name = {
                    "CATALOGUE": "catalogue-input-v1",
                    "INVENTORY": "inventory-input-v1",
                    "ASSURANCE": "qualification-v1",
                }[owner]
                if schema_name is not None:
                    if (owner, schema_name) not in {
                        ("INVENTORY", "migration-input-v3"),
                        ("ASSURANCE", "migration-support-v1"),
                    }:
                        raise ValueError
                    name = schema_name
                schema = json.loads(
                    files("planning.infrastructure.inputs").joinpath(name + ".json").read_text()
                )
                if not Draft202012Validator(schema, format_checker=FormatChecker()).is_valid(
                    result
                ):
                    raise ValueError
            return result
        finally:
            connection.close()
    except Rejected:
        raise
    except (KeyError, ValueError, TypeError, OSError, http.client.HTTPException):
        raise Rejected("source_authority_unavailable", 503) from None


class GovernanceAuthority:
    def caller(self, credential: str, audience: str = "console") -> None:
        try:
            expected = mounted_secret("PLANNING_" + audience.upper() + "_CREDENTIAL_FILE")
            outgoing = mounted_secret("PLANNING_GOVERNANCE_CREDENTIAL_FILE")
            if (
                expected == outgoing
                or not re.fullmatch(r"[A-Za-z0-9_-]{32,4096}", expected)
                or not hmac.compare_digest(expected, credential)
            ):
                raise Rejected("invalid_workload", 401)
        except (KeyError, ValueError, OSError):
            raise Rejected("authority_unavailable", 503) from None

    def actor(
        self,
        credential: str,
        delegation: str,
        tenant: str,
        action: str,
        application: str,
        environment: str,
        site: str,
    ) -> Actor:
        self.caller(credential)
        for value in (tenant, application, environment, site):
            identifier(value)
        if not re.fullmatch("[0-9a-f]{64}", delegation):
            raise Rejected("access_denied", 403)
        scope = {"site_id": site, "environment": environment, "resource_id": application}
        body = request(
            "GOVERNANCE",
            "POST",
            f"/v1/tenants/{tenant}/delegated-authorizations",
            {"action": action, "scope": scope},
            delegation,
        )
        expected = {
            "allowed": True,
            "audience": "planning",
            "delegating_service": "console",
            "authority_use": "request_bound",
            "tenant_id": tenant,
            "action": action,
            "scope": scope,
        }
        try:
            if any(body.get(k) != v for k, v in expected.items()):
                raise ValueError
            expiry = datetime.fromisoformat(body["expires_at"].replace("Z", "+00:00")).timestamp()
            evaluated = datetime.fromisoformat(
                body["evaluated_at"].replace("Z", "+00:00")
            ).timestamp()
            now = time.time()
            if not now < expiry <= now + 65 or abs(now - evaluated) > 5:
                raise ValueError
            return Actor(tenant, identifier(body["actor_id"]), action, application, environment)
        except (ValueError, KeyError, TypeError):
            raise Rejected("authority_unavailable", 503) from None


class OwnerSources:
    def resolve(
        self,
        actor: Actor,
        revision: str,
        candidates: list[dict[str, Any]],
        delegations: dict[str, str],
        action: str,
        method: str,
    ) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        try:
            path = Path(os.environ["PLANNING_REGISTRY_FILE"])
            if not path.is_absolute() or path.stat().st_size > 524288:
                raise ValueError
            registry = decode(path.read_bytes())
            if registry["schema_version"] != 1:
                raise ValueError
            first = candidates[0]
            base = (
                f"/v1/tenants/{actor.tenant}/planning-inputs/"
                f"{actor.application}/{actor.environment}"
            )
            intent = request(
                "CATALOGUE",
                "GET",
                base + f"/{first['site_id']}/{revision}",
                delegation=delegations[first["site_id"]],
                action=actor.action,
            )
            if (
                intent["id"] != revision
                or intent["application_id"] != actor.application
                or intent["intent"]["environment"]["id"] != actor.environment
                or intent["digest"]
                != hashlib.sha256(
                    json.dumps(
                        intent["intent"], sort_keys=True, ensure_ascii=False, separators=(",", ":")
                    )
                    .replace("\u2028", "\\u2028")
                    .replace("\u2029", "\\u2029")
                    .encode()
                ).hexdigest()
            ):
                raise ValueError
            results = []
            for candidate in candidates:
                site = candidate["site_id"]
                destination = request(
                    "INVENTORY",
                    "GET",
                    base + f"/{site}/{candidate['endpoint_id']}/{candidate['generation_id']}",
                    delegation=delegations[site],
                    action=actor.action,
                )
                if destination["tenant_id"] != actor.tenant or any(
                    destination[k] != v for k, v in candidate.items()
                ):
                    raise ValueError
                selected = [
                    row
                    for row in registry["assignments"]
                    if row["tenant_id"] == actor.tenant
                    and row["site_id"] == site
                    and row["endpoint_id"] == candidate["endpoint_id"]
                ]
                if len(selected) != 1:
                    raise Rejected("destination_policy_unassigned", 503)
                assignment = selected[0]
                spec = registry["profiles"][assignment["profile"]]
                p = profile(spec["platform"], spec["version"], spec["declarations"])
                policy = registry["policies"][assignment["policy"]]
                qualification = request(
                    "ASSURANCE",
                    "POST",
                    f"/v1/tenants/{actor.tenant}/planning-qualification",
                    {
                        "scope": {
                            "site_id": site,
                            "environment": actor.environment,
                            "resource_id": actor.application,
                        },
                        "action": actor.action,
                        "qualification_scope": {
                            **{
                                k: destination[k]
                                for k in (
                                    "tenant_id",
                                    "site_id",
                                    "endpoint_id",
                                    "native_scope",
                                    "installed_tuple",
                                )
                            },
                            "action": action,
                            "method": method,
                            "profile_digest": p["digest"],
                            "artifacts": policy["artifacts"],
                        },
                    },
                    delegations[site],
                    actor.action,
                )
                results.append(
                    {
                        "destination": destination,
                        "profile": p,
                        "policy": policy,
                        "qualification": qualification,
                    }
                )
            return intent, results
        except Rejected:
            raise
        except (KeyError, ValueError, TypeError, OSError, IndexError):
            raise Rejected("invalid_owner_input", 503) from None
