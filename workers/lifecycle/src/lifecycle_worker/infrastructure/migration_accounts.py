"""Read-only commissioning of exact source/target accounts from the placed worker.

Role names are not treated as proof of OpenStack write permissions. These probes
prove identity, scope, connectivity and enumerated VMware privilege observations;
native create/delete/fence qualification is an independent acceptance obligation.
"""

import hashlib
import re
import time
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any

from lifecycle_worker.application.api_plan import shape as validate_shape
from lifecycle_worker.application.native import (
    NativeHeld,
    decode,
    digest,
    identity,
    native_identity,
)
from lifecycle_worker.infrastructure.migration_bootstrap import endpoint
from lifecycle_worker.infrastructure.native_files import protected_read
from lifecycle_worker.infrastructure.native_http import NativeReads, credential
from lifecycle_worker.infrastructure.native_json import NativeJson
from lifecycle_worker.infrastructure.native_runtime import endpoints

ROLES = {"collector", "writer", "observer"}
ENTITIES = {
    "VirtualMachine",
    "Folder",
    "Datastore",
    "ResourcePool",
    "Network",
    "DistributedVirtualPortgroup",
}


def text(value: Any, pattern: str) -> str:
    if not isinstance(value, str) or re.fullmatch(pattern, value) is None:
        raise NativeHeld("invalid_migration_account_scope")
    return value


class MigrationAccountProbe:
    def __init__(self, path: Path, clock: Callable[[], int] = lambda: int(time.time())) -> None:
        self.path, self.clock = path, clock

    def run(self) -> dict[str, Any]:
        raw = protected_read(self.path, 262144)
        config = decode(raw)
        shape(config, {"schema_version", "scope", "expires_at", "source", "target"})
        version = config["schema_version"]
        if type(version) is not int or version not in {1, 2, 3}:
            raise NativeHeld("invalid_account_manifest")
        scope = shape(config["scope"], {"tenant_id", "site_id", "environment", "executor_id"})
        for value in scope.values():
            identity(value)
        if type(config["expires_at"]) is not int:
            raise NativeHeld("invalid_account_manifest")

        def current() -> None:
            if self.clock() >= config["expires_at"] or protected_read(self.path, 262144) != raw:
                raise NativeHeld("account_commissioning_changed")

        current()
        environments = {}
        credentials: set[str] = set()
        users: set[str] = set()
        pinned_credentials: dict[Path, str] = {}
        for side in ("source", "target"):
            row = config[side]
            platform = (
                row.get("platform")
                if version == 3
                else ("vmware" if side == "source" else "ahv" if version == 2 else "openstack")
            )
            fields = {"accounts"} | (
                {"api_version", "instance_uuid", "session_manager", "authorization_manager"}
                if platform == "vmware"
                else {"project_id", "prism_central_id", "cluster_id"}
                if platform == "ahv"
                else {"project_id"}
            )
            shape(row, fields | ({"platform"} if version == 3 or platform == "ahv" else set()))
            if platform not in {"vmware", "openstack", "ahv"}:
                raise NativeHeld("invalid_account_manifest")
            if platform == "vmware":
                text(row["api_version"], r"[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+")
                identity(row["instance_uuid"])
                for field in ("session_manager", "authorization_manager"):
                    text(row[field], r"[A-Za-z0-9_-]{1,80}")
            else:
                native_identity(row["project_id"])
                if platform == "ahv":
                    if row["platform"] != "ahv":
                        raise NativeHeld("invalid_account_manifest")
                    identity(row["prism_central_id"])
                    identity(row["cluster_id"])
            shape(row["accounts"], ROLES)
            origins = set()
            for account in row["accounts"].values():
                shape(
                    account,
                    {"user_name", "endpoint", "privileges"}
                    if platform == "vmware"
                    else {
                        "user_id",
                        "key_id",
                        "credential_sha256",
                        "authorization_policies",
                        "endpoint",
                    }
                    if platform == "ahv"
                    else {"user_id", "endpoints", "roles"} | ({"image"} if version == 3 else set()),
                )
                principal = (
                    text(account["user_name"], r"[^\x00-\x20\x7f]{1,200}")
                    if platform == "vmware"
                    else native_identity(account["user_id"])
                )
                connections = (
                    {"api": endpoint(account["endpoint"])}
                    if platform != "openstack"
                    else endpoints(account["endpoints"])
                    | ({"image": endpoint(account["image"])} if "image" in account else {})
                )
                origin = digest(
                    {k: [v.base_url, v.address, str(v.ca_file)] for k, v in connections.items()}
                )
                origins.add(origin)
                principal_key = platform + ":" + origin + ":" + principal.casefold()
                if principal_key in users:
                    raise NativeHeld("distinct_migration_accounts_required")
                users.add(principal_key)
                tokens = {credential(connection) for connection in connections.values()}
                if len(tokens) != 1:
                    raise NativeHeld("one_migration_account_token_required")
                fingerprint = hashlib.sha256(tokens.pop().encode()).hexdigest()
                if fingerprint in credentials:
                    raise NativeHeld("distinct_migration_credentials_required")
                credentials.add(fingerprint)
                for connection in connections.values():
                    pinned_credentials[connection.token_file] = fingerprint
            if len(origins) != 1:
                raise NativeHeld("migration_account_environment_changed")
            environments[side] = (platform, row)

        def guarded() -> None:
            current()
            for path, expected in pinned_credentials.items():
                if (
                    hashlib.sha256(protected_read(path, 4096).rstrip(b"\r\n")).hexdigest()
                    != expected
                ):
                    raise NativeHeld("migration_account_credential_changed")

        results = []
        for side, (platform, row) in environments.items():
            for role in sorted(ROLES):
                guarded()
                result = (
                    self.vmware(row, role, guarded)
                    if platform == "vmware"
                    else self.ahv(row, role, guarded)
                    if platform == "ahv"
                    else self.openstack(row, role, guarded)
                )
                results.append({"side": side, "platform": platform, **result})
        guarded()
        return {
            "schema_version": 1,
            "scope": scope,
            "manifest_sha256": digest(config),
            "observed_at": self.clock(),
            "accounts": results,
            "accounts_checked": True,
            "native_effects_qualified": False,
            "native_write_authorized": False,
        }

    def vmware(
        self, source: dict[str, Any], role: str, current: Callable[[], None]
    ) -> dict[str, Any]:
        account = source["accounts"][role]
        api = NativeJson(endpoint(account["endpoint"]), "vmware-api-session-id")
        api.expected_token_sha256 = hashlib.sha256(api.credential().encode()).hexdigest()
        root = "/sdk/vim25/" + source["api_version"] + "/"
        session = api.request(
            "GET",
            root + "SessionManager/" + source["session_manager"] + "/currentSession",
            current,
        )
        content = api.request("GET", root + "ServiceInstance/ServiceInstance/content", current)
        if (
            not isinstance(session, dict)
            or session.get("userName") != account["user_name"]
            or not isinstance(content, dict)
            or content.get("about", {}).get("instanceUuid") != source["instance_uuid"]
        ):
            raise NativeHeld("vmware_account_identity_changed")
        checks = account["privileges"]
        if not isinstance(checks, list) or not 1 <= len(checks) <= 16:
            raise NativeHeld("explicit_vmware_privileges_required")
        evidence = []
        entities = set()
        for check in checks:
            shape(check, {"entity", "required", "forbidden"})
            entity = shape(check["entity"], {"type", "value"})
            if entity["type"] not in ENTITIES or digest(entity) in entities:
                raise NativeHeld("invalid_privilege_entity")
            entities.add(digest(entity))
            text(entity["value"], r"[A-Za-z0-9_-]{1,80}")
            for name in ("required", "forbidden"):
                values = check[name]
                if (
                    not isinstance(values, list)
                    or len(values) > 64
                    or len(set(values)) != len(values)
                ):
                    raise NativeHeld("invalid_privilege_inventory")
                for value in values:
                    text(value, r"[A-Za-z0-9_.]{1,120}")
            required, forbidden = set(check["required"]), set(check["forbidden"])
            if not required or required & forbidden:
                raise NativeHeld("invalid_privilege_inventory")
            result = api.request(
                "POST",
                root
                + "AuthorizationManager/"
                + source["authorization_manager"]
                + "/HasUserPrivilegeOnEntities",
                current,
                {
                    "entities": [entity],
                    "userName": account["user_name"],
                    "privId": sorted(required | forbidden),
                },
            )
            if not isinstance(result, list) or len(result) != 1 or not isinstance(result[0], dict):
                raise NativeHeld("privilege_observation_incomplete")
            observed = result[0]
            if {k: observed.get("entity", {}).get(k) for k in ("type", "value")} != entity:
                raise NativeHeld("privilege_entity_changed")
            permissions = observed.get("privAvailability")
            if not isinstance(permissions, list) or len(permissions) != len(required | forbidden):
                raise NativeHeld("privilege_observation_incomplete")
            mapped = {p["privId"]: p["isGranted"] for p in permissions}
            if (
                set(mapped) != required | forbidden
                or not all(type(v) is bool for v in mapped.values())
                or any(mapped[p] is not True for p in required)
                or any(mapped[p] is not False for p in forbidden)
            ):
                raise NativeHeld("vmware_privilege_scope_denied")
            evidence.append({"entity": entity, "privileges": mapped})
        return {
            "role": role,
            "identity_sha256": digest(account["user_name"]),
            "scope_sha256": digest(source["instance_uuid"]),
            "evidence_sha256": digest(evidence),
        }

    def ahv(self, target: dict[str, Any], role: str, current: Callable[[], None]) -> dict[str, Any]:
        account = target["accounts"][role]
        from lifecycle_worker.infrastructure.ahv_accounts import probe
        from lifecycle_worker.infrastructure.ahv_http import AhvHttp, read

        connection = endpoint(account["endpoint"])
        api_ahv = AhvHttp(connection, read_only=True)
        evidence_ahv = probe(api_ahv, account, connection, self.clock, current)
        for namespace, resource, field in (
            ("prism", "domain-managers", "prism_central_id"),
            ("clustermgmt", "clusters", "cluster_id"),
        ):
            observed_ahv = read(
                api_ahv,
                "/api/" + namespace + "/v4.3/config/" + resource + "/" + target[field],
                current,
            )
            if observed_ahv.get("extId") != target[field]:
                raise NativeHeld("ahv_destination_identity_changed")
        return {
            "role": role,
            **evidence_ahv,
            "scope_sha256": digest(
                [target["project_id"], target["prism_central_id"], target["cluster_id"]]
            ),
        }

    def openstack(
        self, target: dict[str, Any], role: str, current: Callable[[], None]
    ) -> dict[str, Any]:
        account = target["accounts"][role]
        reads = NativeReads(endpoints(account["endpoints"]), current)
        reads.subject_token_sha256 = hashlib.sha256(
            credential(reads.endpoints["identity"]).encode()
        ).hexdigest()
        token = reads.get("identity", "/auth/tokens", subject=True).get("token", {})
        expiry = datetime.fromisoformat(token.get("expires_at", "").replace("Z", "+00:00"))
        roles = token.get("roles", [])
        allowed = account["roles"]
        if (
            not isinstance(allowed, list)
            or not 1 <= len(allowed) <= 32
            or len(set(allowed)) != len(allowed)
        ):
            raise NativeHeld("explicit_openstack_roles_required")
        for value in allowed:
            text(value, r"[A-Za-z0-9_.-]{1,80}")
        if (
            token.get("user", {}).get("id") != account["user_id"]
            or token.get("project", {}).get("id") != target["project_id"]
            or expiry.tzinfo is None
            or expiry.timestamp() <= self.clock()
            or not isinstance(roles, list)
            or {r["name"] for r in roles} != set(allowed)
        ):
            raise NativeHeld("openstack_account_scope_denied")
        current()
        target_evidence = {}
        for service, path in (
            ("compute", "/limits"),
            ("volume", "/limits"),
            ("network", "/extensions"),
        ):
            current()
            target_evidence[service] = digest(reads.get(service, path))
        if "image" in account:
            image_api = NativeJson(endpoint(account["image"]), "X-Auth-Token")
            image_api.expected_token_sha256 = reads.subject_token_sha256
            target_evidence["image"] = digest(image_api.request("GET", "/schemas/image", current))
        return {
            "role": role,
            "identity_sha256": digest(account["user_id"]),
            "scope_sha256": digest(target["project_id"]),
            "evidence_sha256": digest(target_evidence),
        }


def shape(value: Any, fields: set[str]) -> dict[str, Any]:
    validate_shape(value, fields)
    assert isinstance(value, dict)
    return value
