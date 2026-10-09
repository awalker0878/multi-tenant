"""Pinned, bounded Prism Central transport with fixed v4.3 routes and no redirects."""

import http.client
import json
import re
from collections.abc import Callable
from typing import Any, Protocol
from urllib.parse import urlsplit

from lifecycle_worker.application.native import NativeHeld, decode, identity
from lifecycle_worker.infrastructure.native_http import NativeEndpoint, PinnedConnection, credential
from lifecycle_worker.infrastructure.native_response import response_bytes

UUID = r"[a-f0-9-]{36}"
COLLECTIONS = {"image": "/api/vmm/v4.3/content/images", "server": "/api/vmm/v4.3/ahv/config/vms"}


class AhvTransport(Protocol):
    def call(
        self,
        method: str,
        path: str,
        body: Any,
        headers: dict[str, str],
        boundary: Callable[[], None],
    ) -> dict[str, Any]: ...


class AhvHttp:
    def __init__(
        self, endpoint: NativeEndpoint, read_only: bool = False,
        api_versions: dict[str, str] | None = None,
    ) -> None:
        if urlsplit(endpoint.base_url).path not in {"", "/"}:
            raise NativeHeld("invalid_ahv_origin")
        self.endpoint, self.read_only = endpoint, read_only
        # Enrolled standalone account probes are read-only by default. Native
        # plan execution passes an exact namespace inventory to this transport.
        self.api_versions = api_versions
        if api_versions is not None and (
            not isinstance(api_versions, dict)
            or set(api_versions) != {"vmm", "prism", "clustermgmt",
                                     "networking", "microseg", "iam"}
            or any(not isinstance(v, str)
                   or re.fullmatch(r"v[0-9]+\.[0-9]+", v) is None
                   for v in api_versions.values())
        ):
            raise NativeHeld("ahv_qualified_namespace_manifest_invalid")

    def call(
        self,
        method: str,
        path: str,
        body: Any,
        headers: dict[str, str],
        boundary: Callable[[], None],
    ) -> dict[str, Any]:
        if self.api_versions is not None:
            match = re.fullmatch(
                r"/api/(vmm|prism|clustermgmt|networking|microseg|iam)/"
                r"(v[0-9]+\.[0-9]+)/.*", path,
            )
            if match is None or self.api_versions[match[1]] != match[2]:
                raise NativeHeld("ahv_native_request_version_unqualified")
        create = method == "POST" and path in COLLECTIONS.values()
        objects = any(re.fullmatch(re.escape(p) + "/" + UUID, path) for p in COLLECTIONS.values())
        reads = objects or re.fullmatch(
            r"/api/(?:prism/v4\.3/config/(?:tasks/(?:[A-Za-z0-9:_=-]|%2[BbFf]){1,160}|domain-managers/"
            + UUID
            + r"|categories/"
            + UUID
            + r")|clustermgmt/v4\.3/config/(?:clusters|storage-containers)/"
            + UUID
            + r"|networking/v4\.3/config/(?:subnets|vpcs)/"
            + UUID
            + r"|microseg/v4\.3/config/policies/"
            + UUID
            + r"|iam/v4\.3/(?:authn/users/"
            + UUID
            + r"(?:/keys/"
            + UUID
            + r")?|authz/authorization-policies/"
            + UUID
            + r"))",
            path,
        )
        delete = method == "DELETE" and objects
        if (
            not (create or delete or method == "GET" and reads)
            or self.read_only
            and method != "GET"
            or not set(headers) <= {"Ntnx-Request-Id", "If-Match"}
        ):
            raise NativeHeld("unapproved_ahv_route")
        if method != "GET":
            identity(headers.get("Ntnx-Request-Id"))
        if delete and (not headers.get("If-Match") or len(headers["If-Match"]) > 256):
            raise NativeHeld("ahv_etag_required")
        token = credential(self.endpoint)

        def current() -> None:
            boundary()
            if credential(self.endpoint) != token:
                raise NativeHeld("ahv_credential_changed")

        payload = None if body is None else json.dumps(body, allow_nan=False).encode()
        if payload is not None and len(payload) > 262144:
            raise NativeHeld("ahv_request_bound")
        connection = PinnedConnection(self.endpoint)
        try:
            current()
            connection.request(
                method,
                path,
                body=payload,
                headers={
                    "X-Ntnx-Api-Key": token,
                    "Accept": "application/json",
                    "Accept-Encoding": "identity",
                    "Content-Type": "application/json",
                    **headers,
                },
            )
            response = connection.getresponse()
            if (
                response.status != (200 if method == "GET" else 202)
                or response.getheader("Content-Type", "").split(";")[0] != "application/json"
                or response.getheader("Content-Encoding", "identity") != "identity"
            ):
                raise NativeHeld("ahv_response_requires_reconciliation")
            document = decode(response_bytes(response, 2097152, 10, current))
            return {"document": document, "etag": response.getheader("ETag", "")}
        except (OSError, http.client.HTTPException):
            raise NativeHeld("ahv_response_requires_reconciliation") from None
        finally:
            connection.close()


def read(api: AhvTransport, path: str, boundary: Callable[[], None]) -> dict[str, Any]:
    result = api.call("GET", path, None, {}, boundary)["document"].get("data")
    if not isinstance(result, dict):
        raise NativeHeld("ahv_readback_missing")
    return result
