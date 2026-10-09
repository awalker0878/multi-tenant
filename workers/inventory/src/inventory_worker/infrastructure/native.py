"Pinned TLS, fixed read routes and bounded normalization for selected native APIs."

import http.client
import ipaddress
import json
import os
import re
import socket
import ssl
import time
from collections.abc import Callable
from contextlib import contextmanager
from contextvars import ContextVar
import hashlib
from pathlib import Path
from typing import Any
from urllib.parse import urlencode, urlsplit


# A scoped, lease-local audit sink. ContextVar prevents evidence escaping a
# collection job; it never signs or promotes raw GETs to E3/E4 qualification.
_READ_WITNESS_SINK: ContextVar[Callable[[dict[str, Any]], None] | None] = ContextVar(
    "inventory_native_read_witness_sink", default=None
)


@contextmanager
def capture_native_reads(sink: Callable[[dict[str, Any]], None]):
    token = _READ_WITNESS_SINK.set(sink)
    try:
        yield
    finally:
        _READ_WITNESS_SINK.reset(token)


class CollectionFailure(Exception):
    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


def secret(path: str) -> str:
    if not os.path.isabs(path):
        raise CollectionFailure("unsafe_destination")
    with Path(path).open("rb") as handle:
        raw = handle.read(4097).rstrip(b"\r\n")
    if not 16 <= len(raw) <= 4096 or any(c < 33 or c > 126 for c in raw):
        raise CollectionFailure("permission_denied")
    return raw.decode("ascii")


def strict_json(raw: bytes) -> Any:
    def pairs(values: list[tuple[str, Any]]) -> dict[str, Any]:
        output: dict[str, Any] = {}
        for k, v in values:
            if k in output:
                raise CollectionFailure("invalid_response")
            output[k] = v
        return output

    try:
        return json.loads(
            raw,
            object_pairs_hook=pairs,
            parse_constant=lambda _: (_ for _ in ()).throw(ValueError()),
        )
    except (ValueError, UnicodeError, RecursionError):
        raise CollectionFailure("invalid_response") from None


class PinnedConnection(http.client.HTTPSConnection):
    def __init__(self, host: str, port: int, address: str, ca: str) -> None:
        ip = ipaddress.ip_address(address)
        if ip.is_unspecified or ip.is_multicast or ip.is_link_local or not os.path.isabs(ca):
            raise CollectionFailure("unsafe_destination")
        self.tls_context = ssl.create_default_context(cafile=ca)
        super().__init__(host, port, timeout=3, context=self.tls_context)
        self.address = address

    def connect(self) -> None:
        # Connect to an approved literal address; retain hostname verification/SNI.
        # DNS, environment proxies, redirects and returned hyperlinks cannot retarget it.
        connection = socket.create_connection((self.address, self.port), timeout=3)
        try:
            self.sock = self.tls_context.wrap_socket(connection, server_hostname=self.host)
        except BaseException:
            connection.close()
            raise


def exchange(
    stream: dict[str, Any],
    path: str,
    headers: dict[str, str],
    *,
    method: str = "GET",
    body: dict[str, Any] | None = None,
    version_discovery: bool = False,
) -> Any:
    u = urlsplit(stream["base_url"])
    if u.scheme != "https" or not u.hostname or u.username or u.password or u.query or u.fragment:
        raise CollectionFailure("unsafe_destination")
    if not path.startswith("/") or "\\" in path or ".." in path or "\r" in path or "\n" in path:
        raise CollectionFailure("unsafe_destination")
    connection = PinnedConnection(
        u.hostname, u.port or 443, stream["addresses"][0], stream["ca_file"]
    )
    deadline = time.monotonic() + 10
    try:
        connection.request(
            method,
            u.path.rstrip("/") + path,
            None if body is None else json.dumps(body, allow_nan=False),
            {
                "Accept": "application/json",
                "Accept-Encoding": "identity",
                "Content-Type": "application/json",
                **headers,
            },
        )
        response = connection.getresponse()
        allowed_version = (
            version_discovery and response.status == 300 and not response.getheader("Location")
        )
        if 300 <= response.status < 400 and not allowed_version:
            raise CollectionFailure("unsafe_destination")
        if response.status in {401, 403}:
            raise CollectionFailure("permission_denied")
        if response.status == 404 and version_discovery:
            raise CollectionFailure("unsupported_api")
        if response.status == 429:
            raise CollectionFailure("throttled")
        if response.status >= 500:
            raise CollectionFailure("transport_unavailable")
        if (response.status != 200 and not allowed_version) or response.getheader(
            "Content-Encoding", "identity"
        ) != "identity":
            raise CollectionFailure("invalid_response")
        if not response.getheader("Content-Type", "").lower().startswith("application/json"):
            raise CollectionFailure("invalid_response")
        data = bytearray()
        while True:
            if time.monotonic() >= deadline:
                raise CollectionFailure("transport_unavailable")
            chunk = response.read1(min(65536, 2097153 - len(data)))
            data.extend(chunk)
            if len(data) > 2097152:
                raise CollectionFailure("invalid_response")
            if not chunk:
                break
        observed = strict_json(bytes(data))
        witness = _READ_WITNESS_SINK.get()
        if method == "GET" and witness is not None and len(path) <= 400:
            # The transport has already checked status, TLS peer, scope, and
            # response encoding. This response digest is an audit witness,
            # NOT proof that every manifest field exists inside the document.
            witness({
                "native_operation": "GET " + path,
                "api_version": str(stream.get("api_version", "")),
                "response_sha256": hashlib.sha256(
                    json.dumps(observed, sort_keys=True, separators=(",", ":"),
                               allow_nan=False).encode()
                ).hexdigest(),
                "observed_at": int(time.time()),
            })
        return observed
    except (OSError, http.client.HTTPException):
        raise CollectionFailure("transport_unavailable") from None
    finally:
        connection.close()


def collect(
    policy: dict[str, Any],
    stream_index: int,
    cursor: str | None,
    include_configuration: bool = False,
    before_request: Callable[[], None] | None = None,
) -> dict[str, Any]:
    platform, scope = policy["platform"], policy["native_scope"]
    from inventory_worker.infrastructure.generated_configuration_streams import (
        configuration_streams,
    )

    streams = (
        configuration_streams(policy["streams"], platform)
        if include_configuration
        else policy["streams"]
    )
    stream = streams[stream_index]
    kind = stream["kind"]
    if kind in {"source_profile", "target_profile"}:
        from inventory_worker.infrastructure.profile_collection import collect_profile

        if before_request is None:
            raise CollectionFailure("permission_denied")
        return collect_profile(policy, stream, cursor, before_request)
    if kind.startswith("config_"):
        from inventory_worker.infrastructure.configuration import collect_configuration

        if cursor is not None:
            raise CollectionFailure("invalid_response")
        return collect_configuration(policy, stream)
    if not re.fullmatch(r"[A-Za-z0-9_.:-]{1,200}", scope) or (
        cursor is not None and not re.fullmatch(r"[A-Za-z0-9_.:-]{1,200}", cursor)
    ):
        raise CollectionFailure("unsafe_destination")
    token = secret(stream["credential_file"])
    if platform == "ahv" and kind == "server":
        if stream["api_version"] not in {"v4.2", "v4.3"}:
            raise CollectionFailure("unsupported_api")
        from inventory_worker.infrastructure.ahv_workload import read_vm

        source = next((s for s in policy["streams"] if s["kind"] == "source_profile"), None)
        if source is None or (cursor is not None and cursor not in source["vm_ids"]):
            raise CollectionFailure("unsafe_destination")
        index = source["vm_ids"].index(cursor) + 1 if cursor else 0
        if index >= len(source["vm_ids"]):
            raise CollectionFailure("invalid_response")
        vm = source["vm_ids"][index]
        row = read_vm(stream, vm, scope)
        last = index + 1 == len(source["vm_ids"])
        return {
            "observations": [
                {
                    "kind": "server",
                    "native_id": vm,
                    "incarnation": row.get("generationUuid"),
                    "name": row.get("name") or vm,
                    "scope": scope,
                    "facts": {"power": row.get("powerState", "UNKNOWN")},
                }
            ],
            "next_cursor": None if last else vm,
            "terminal": last,
            "coverage": policy["coverage_reference"] is not None,
            "collected_at": time.time(),
            "error": None,
        }
    if platform == "openstack":
        route, collection = {
            "server": ("/servers/detail", "servers"),
            "network": ("/networks", "networks"),
            "volume": ("/volumes/detail", "volumes"),
        }[kind]
        # Compute 2.1 and Cinder 3.0 are explicit baselines, never silently negotiated.
        versions = {"server": "2.1", "network": "2.0", "volume": "3.0"}
        if stream["api_version"] != versions[kind]:
            raise CollectionFailure("unsupported_api")
        params = {"limit": "100"}
        if cursor:
            params["marker"] = cursor
        if kind == "network":
            params["project_id"] = scope
        if kind == "volume" and not urlsplit(stream["base_url"]).path.endswith("/" + scope):
            raise CollectionFailure("unsafe_destination")
        headers = {"X-Auth-Token": token}
        if kind == "server":
            headers["OpenStack-API-Version"] = "compute 2.1"
        if kind == "volume":
            headers["OpenStack-API-Version"] = "volume 3.0"
        response = exchange(stream, route + "?" + urlencode(params), headers)
        if not isinstance(response, dict) or not isinstance(response.get(collection), list):
            raise CollectionFailure("invalid_response")
        rows = response[collection]
        # Continue until an actual empty terminal page, even when a provider lowers the limit.
        terminal = not rows
    elif platform == "vmware":
        if stream["api_version"] != "vcenter-api" or cursor is not None:
            raise CollectionFailure("unsupported_api")
        route = {"server": "vm", "network": "network", "datastore": "datastore"}[kind]
        rows = exchange(
            stream,
            "/api/vcenter/" + route + "?" + urlencode({"datacenters": scope}),
            {"vmware-api-session-id": token},
        )
        terminal = True
    else:
        raise CollectionFailure("unsupported_api")
    if not isinstance(rows, list) or len(rows) > 100:
        # No truncation: REST lists without native continuation remain an explicit limit.
        raise CollectionFailure("invalid_response")
    observations = []
    for row in rows:
        if not isinstance(row, dict):
            raise CollectionFailure("invalid_response")
        if platform == "openstack":
            reported = row.get(
                "project_id", row.get("tenant_id", row.get("os-vol-tenant-attr:tenant_id"))
            )
            if reported is not None and reported != scope:
                raise CollectionFailure("permission_denied")
            if kind in {"server", "network"} and reported != scope:
                raise CollectionFailure("permission_denied")
            native = row.get("id")
            incarnation = row.get("created", row.get("created_at"))
            facts = {
                k: row[source]
                for k, source in {"status": "status", "size_gib": "size"}.items()
                if source in row
            }
        else:
            native = row.get({"server": "vm", "network": "network", "datastore": "datastore"}[kind])
            # List endpoints do not expose an incarnation: retain an identity hold.
            incarnation = None
            facts = {
                k: row[source]
                for k, source in {
                    "power": "power_state",
                    "cpu": "cpu_count",
                    "memory_mib": "memory_size_MiB",
                }.items()
                if source in row
            }
        if not isinstance(native, str) or not re.fullmatch(r"[A-Za-z0-9_.:-]{1,200}", native):
            raise CollectionFailure("invalid_response")
        name = row.get("name") or native
        if not isinstance(name, str) or len(name) > 255 or any(ord(c) < 32 for c in name):
            raise CollectionFailure("invalid_response")
        observations.append(
            {
                "kind": kind,
                "native_id": native,
                "incarnation": incarnation,
                "name": name,
                "scope": scope,
                "facts": facts,
            }
        )
    return {
        "observations": observations,
        "next_cursor": None if terminal else observations[-1]["native_id"],
        "terminal": terminal,
        "coverage": policy["coverage_reference"] is not None,
        "collected_at": time.time(),
        "error": None,
    }
