"A read-only, separately administered policy mount is the outbound trust authority."

import ipaddress
import json
import os
import re
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from inventory.domain.discovery import (
    EnrollmentPolicy,
    Rejected,
    digest,
    identifier,
    number,
    shape,
    text,
)


def load_document(path: str, maximum: int = 1048576) -> Any:
    if not os.path.isabs(path):
        raise Rejected("policy_unavailable", 503)
    with Path(path).open("rb") as handle:
        raw = handle.read(maximum + 1)
    if len(raw) > maximum:
        raise Rejected("policy_unavailable", 503)

    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in items:
            if key in result:
                raise Rejected("duplicate_json_key")
            result[key] = value
        return result

    return json.loads(
        raw,
        object_pairs_hook=pairs,
        parse_constant=lambda _: (_ for _ in ()).throw(ValueError("Non-finite JSON")),
    )


def parse_policy(value: Any) -> EnrollmentPolicy:
    fields = {
        "policy_id",
        "tenant",
        "site",
        "owner",
        "worker",
        "worker_fingerprint",
        "epoch",
        "platform",
        "native_scope",
        "authority",
        "installed",
        "streams",
        "freshness_seconds",
        "requests_per_minute",
        "concurrency",
        "tenant_concurrency",
        "max_pages",
        "expires_at",
        "coverage_reference",
    }
    p = shape(value, fields)
    for key in ("policy_id", "tenant", "site", "owner", "worker", "epoch"):
        identifier(p[key])
    if p["platform"] not in {"openstack", "vmware", "ahv"}:
        raise Rejected("unknown_platform")
    for key in ("native_scope", "authority"):
        if not re.fullmatch(r"[A-Za-z0-9_.:-]{1,200}", text(p[key])):
            raise Rejected("invalid_native_scope")
    if not isinstance(p["worker_fingerprint"], str) or not re.fullmatch(
        r"[0-9a-f]{64}", p["worker_fingerprint"]
    ):
        raise Rejected("invalid_worker_fingerprint")
    installed = shape(
        p["installed"],
        {"product", "api", "backend", "features", "entitlements", "configuration_reference"},
    )
    for key, val in installed.items():
        if key in {"features", "entitlements"}:
            if not isinstance(val, list) or len(val) > 50:
                raise Rejected("invalid_installed_identity")
            for item in val:
                text(item)
        else:
            text(val)
    number(p["freshness_seconds"], 60, 3600)
    number(p["requests_per_minute"], 1, 600)
    number(p["concurrency"], 1, 16)
    number(p["tenant_concurrency"], 1, 4)
    number(p["max_pages"], 1, 100)
    if type(p["expires_at"]) not in {float, int} or p["expires_at"] <= 0:
        raise Rejected("invalid_policy_expiry")
    if p["coverage_reference"] is not None:
        text(p["coverage_reference"])
    streams = p["streams"]
    required = {
        "openstack": {"server", "network", "volume"},
        "vmware": {"server", "network", "datastore"},
        "ahv": set(),
    }[p["platform"]]
    if (
        not isinstance(streams, list)
        or {s.get("kind") for s in streams if isinstance(s, dict)} != required
        or len(streams) != len(required)
    ):
        raise Rejected("invalid_stream_coverage")
    for s in streams:
        shape(s, {"kind", "base_url", "addresses", "ca_file", "credential_file", "api_version"})
        u = urlsplit(text(s["base_url"], 512))
        if (
            u.scheme != "https"
            or not u.hostname
            or u.username
            or u.password
            or u.query
            or u.fragment
            or "\\" in s["base_url"]
        ):
            raise Rejected("invalid_native_origin")
        if (
            not re.fullmatch(r"[A-Za-z0-9./:_-]*", u.path)
            or ".." in u.path
            or (u.port is not None and not 1 <= u.port <= 65535)
        ):
            raise Rejected("invalid_native_origin")
        if not isinstance(s["addresses"], list) or not 1 <= len(s["addresses"]) <= 16:
            raise Rejected("invalid_native_addresses")
        for address in s["addresses"]:
            ip = ipaddress.ip_address(address)
            if ip.is_unspecified or ip.is_multicast or ip.is_link_local:
                raise Rejected("invalid_native_addresses")
        for field in ("ca_file", "credential_file"):
            if not os.path.isabs(text(s[field], 512)):
                raise Rejected("invalid_secret_reference")
        text(s["api_version"], 40)
    return EnrollmentPolicy(**p, policy_digest=digest(p))


class MountedPolicies:
    def __init__(self, path: str | None = None) -> None:
        self.path = path

    def load(self) -> dict[str, EnrollmentPolicy]:
        try:
            data = shape(
                load_document(self.path or os.environ["INVENTORY_SITE_POLICIES_FILE"]),
                {"version", "policies"},
            )
            if (
                data["version"] != 1
                or not isinstance(data["policies"], list)
                or len(data["policies"]) > 1000
            ):
                raise ValueError("Invalid policies")
            result: dict[str, EnrollmentPolicy] = {}
            origins: dict[str, str] = {}
            authorities: dict[str, tuple[int, int]] = {}
            workers: dict[str, str] = {}
            for raw in data["policies"]:
                p = parse_policy(raw)
                if p.policy_id in result:
                    raise ValueError("Duplicate policy")
                # Shared endpoints cannot acquire different aggregate budget identities.
                for stream in p.streams:
                    u = urlsplit(stream["base_url"])
                    origin = f"{u.hostname}:{u.port or 443}"
                    if origins.setdefault(origin, p.authority) != p.authority:
                        raise ValueError("Split endpoint budget")
                if authorities.setdefault(p.authority, (p.requests_per_minute, p.concurrency)) != (
                    p.requests_per_minute,
                    p.concurrency,
                ):
                    raise ValueError("Conflicting endpoint budget")
                if workers.setdefault(p.worker_fingerprint, p.worker) != p.worker:
                    raise ValueError("Shared worker credential")
                if p.expires_at > time.time():
                    result[p.policy_id] = p
            return result
        except (KeyError, ValueError, TypeError, OSError, Rejected, RecursionError):
            raise Rejected("policy_unavailable", 503) from None
