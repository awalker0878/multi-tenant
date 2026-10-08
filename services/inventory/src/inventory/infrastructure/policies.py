"A read-only, separately administered policy mount is the outbound trust authority."

import ipaddress
import json
import os
import re
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from inventory.domain.ahv import native_uuid
from inventory.domain.configuration import CONFIGURATION_QUERIES
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
    if not isinstance(streams, list):
        raise Rejected("invalid_stream_coverage")
    required = {
        "openstack": {"server", "network", "volume"},
        "vmware": {"server", "network", "datastore"},
        "ahv": {"server"}
        if any(s.get("kind") == "source_profile" for s in p["streams"] if isinstance(s, dict))
        else {"target_profile"},
    }[p["platform"]]
    allowed = (
        required
        | ({"source_profile", "target_profile"})
        | (
            {"config_" + q for q in CONFIGURATION_QUERIES}
            if p["platform"] == "openstack"
            else set()
        )
    )
    kinds = (
        [s.get("kind") for s in streams if isinstance(s, dict)] if isinstance(streams, list) else []
    )
    if (
        not isinstance(streams, list)
        or not required <= set(kinds)
        or set(kinds) - allowed
        or len(kinds) != len(streams)
        or len(kinds) != len(set(kinds))
    ):
        raise Rejected("invalid_stream_coverage")
    for s in streams:
        shape(
            s,
            {"kind", "base_url", "addresses", "ca_file", "credential_file", "api_version"}
            | ({"vm_ids"} if s["kind"] == "source_profile" else set())
            | (
                {"cluster_id", "prism_central_id", "shared_resource_ids"}
                if p["platform"] == "ahv"
                else set()
            ),
        )
        if s["kind"] == "source_profile":
            vms = s["vm_ids"]
            if (
                not isinstance(vms, list)
                or not 1 <= len(vms) <= 32
                or not all(
                    isinstance(v, str)
                    and re.fullmatch(
                        r"vm-[0-9]+"
                        if p["platform"] == "vmware"
                        else r"[a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12}",
                        v,
                    )
                    for v in vms
                )
                or len(set(vms)) != len(vms)
            ):
                raise Rejected("invalid_vm_allowlist")
            if p["platform"] == "vmware" and (
                not isinstance(s["api_version"], str)
                or not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+", s["api_version"])
            ):
                raise Rejected("explicit_vi_release_required")
            if "server" not in kinds or streams.index(s) < kinds.index("server"):
                raise Rejected("profile_scope_not_ready")
            if p["platform"] == "vmware" and urlsplit(s["base_url"]).path not in {"", "/"}:
                raise Rejected("profile_scope_not_ready")
            server = streams[kinds.index("server")]
            source_url, server_url = urlsplit(s["base_url"]), urlsplit(server["base_url"])
            if p["platform"] == "openstack" and (
                s["api_version"] != "2.1" or s["base_url"] != server["base_url"]
            ):
                raise Rejected("explicit_nova_source_scope_required")
            if (source_url.hostname, source_url.port or 443, s["addresses"], s["ca_file"]) != (
                server_url.hostname,
                server_url.port or 443,
                server["addresses"],
                server["ca_file"],
            ):
                raise Rejected("profile_vcenter_scope_mismatch")
        if (
            s["kind"] == "target_profile"
            and p["platform"] == "vmware"
            and (
                not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+", s["api_version"])
                or urlsplit(s["base_url"]).path not in {"", "/"}
                or not re.fullmatch(r"datacenter-[0-9]+", p["native_scope"])
            )
        ):
            raise Rejected("explicit_vmware_destination_scope_required")
        if p["platform"] == "ahv":
            for field in ("cluster_id", "prism_central_id"):
                native_uuid(s[field])
            native_uuid(p["native_scope"])
            shared = s["shared_resource_ids"]
            if not isinstance(shared, list) or len(shared) > 100 or len(set(shared)) != len(shared):
                raise Rejected("invalid_ahv_shared_resources")
            for key in shared:
                native_uuid(key)
            if s["api_version"] != "v4.3" or urlsplit(s["base_url"]).path not in {"", "/"}:
                raise Rejected("explicit_ahv_v43_required")
        if (
            s["kind"] == "target_profile"
            and p["platform"] == "openstack"
            and (s["api_version"] != "2" or urlsplit(s["base_url"]).path.rstrip("/") != "/v2")
        ):
            raise Rejected("explicit_glance_v2_required")
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
            tenants: dict[str, int] = {}
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
                if tenants.setdefault(p.tenant, p.tenant_concurrency) != p.tenant_concurrency:
                    raise ValueError("Conflicting tenant budget")
                if p.expires_at > time.time():
                    result[p.policy_id] = p
            return result
        except (KeyError, ValueError, TypeError, OSError, Rejected, RecursionError):
            raise Rejected("policy_unavailable", 503) from None
