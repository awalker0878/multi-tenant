"""Revocable read-only Lifecycle grants scoped to one confirmed migration review."""

import hmac
import json
import os
import re
import stat
import time
from pathlib import Path
from typing import Any

from inventory.domain.discovery import Rejected, identifier, number, shape


def protected(path: str, maximum: int) -> bytes:
    file = Path(path)
    if not file.is_absolute() or any(p.is_symlink() for p in (file, *file.parents)):
        raise ValueError
    fd = os.open(file, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, "rb") as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_mode & 0o022:
            raise ValueError
        value = stream.read(maximum + 1)
        if len(value) > maximum:
            raise ValueError
        return value


def decode(raw: bytes) -> dict[str, Any]:
    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in items:
            if key in result:
                raise ValueError
            result[key] = value
        return result

    def invalid(_: str) -> None:
        raise ValueError

    result = json.loads(raw, object_pairs_hook=pairs, parse_constant=invalid)
    if not isinstance(result, dict):
        raise ValueError
    return result


def native_reader(
    token: str,
    tenant: str,
    application: str,
    environment: str,
    site: str,
    revision: int,
    content_digest: str,
) -> None:
    try:
        config = decode(protected(os.environ["INVENTORY_NATIVE_READERS_FILE"], 1048576))
        shape(config, {"schema_version", "grants"})
        number(config["schema_version"], 1, 1)
        grants = config["grants"]
        if not isinstance(grants, list) or not 1 <= len(grants) <= 256:
            raise ValueError
        tokens, matches, readers = [], [], set()
        for grant in grants:
            shape(grant, {"reader_id", "token_file", "expires_at", "scopes"})
            reader = identifier(grant["reader_id"])
            if reader in readers:
                raise ValueError
            readers.add(reader)
            number(grant["expires_at"], 1, 2**53 - 1)
            scopes = grant["scopes"]
            if not isinstance(scopes, list) or not 1 <= len(scopes) <= 1000:
                raise ValueError
            unique = set()
            for scope in scopes:
                shape(
                    scope,
                    {"tenant_id", "application_id", "environment", "site_id", "revision", "digest"},
                )
                for field in ("tenant_id", "application_id", "environment", "site_id"):
                    identifier(scope[field])
                number(scope["revision"], 1, 2**31 - 1)
                if not isinstance(scope["digest"], str) or not re.fullmatch(
                    r"[a-f0-9]{64}", scope["digest"]
                ):
                    raise ValueError
                key = tuple(scope[k] for k in sorted(scope))
                if key in unique:
                    raise ValueError
                unique.add(key)
            secret = protected(grant["token_file"], 4098).decode("ascii").rstrip("\r\n")
            if not re.fullmatch(r"[A-Za-z0-9_-]{32,4096}", secret):
                raise ValueError
            tokens.append(secret)
            if hmac.compare_digest(token, secret):
                matches.append(grant)
        if len(set(tokens)) != len(tokens) or len(matches) != 1:
            raise Rejected("native_reader_denied", 403)
        expected: dict[str, Any] = {
            "tenant_id": tenant,
            "application_id": application,
            "environment": environment,
            "site_id": site,
            "revision": revision,
            "digest": content_digest,
        }
        if expected not in matches[0]["scopes"] or matches[0]["expires_at"] <= time.time():
            raise Rejected("native_reader_scope_denied", 403)
    except Rejected:
        raise
    except Exception:
        raise Rejected("native_reader_unavailable", 503) from None


def capability_reader(
    token: str,
    tenant: str,
    application: str,
    environment: str,
    site: str,
    endpoint: str,
    generation: str,
) -> None:
    """A separate revocable service grant for one pinned capability generation."""
    try:
        registry = decode(protected(os.environ["INVENTORY_CAPABILITY_READERS_FILE"], 1048576))
        shape(registry, {"schema_version", "grants"})
        number(registry["schema_version"], 1, 1)
        expected = {
            "tenant_id": tenant,
            "application_id": application,
            "environment": environment,
            "site_id": site,
            "endpoint_id": endpoint,
            "generation_id": generation,
        }
        for value in expected.values():
            identifier(value)
        grants = registry["grants"]
        if not isinstance(grants, list) or not 1 <= len(grants) <= 256:
            raise ValueError
        selected = []
        tokens = []
        for grant in grants:
            shape(grant, {"token_file", "expires_at", "scopes"})
            secret = protected(grant["token_file"], 4098).decode("ascii").rstrip("\r\n")
            if not re.fullmatch(r"[A-Za-z0-9_-]{32,4096}", secret):
                raise ValueError
            tokens.append(secret)
            if hmac.compare_digest(token, secret):
                selected.append(grant)
        if len(set(tokens)) != len(tokens) or len(selected) != 1:
            raise Rejected("capability_reader_denied", 403)
        grant = selected[0]
        if (
            type(grant["expires_at"]) is not int
            or grant["expires_at"] <= time.time()
            or expected not in grant["scopes"]
        ):
            raise Rejected("capability_reader_scope_denied", 403)
    except Rejected:
        raise
    except Exception:
        raise Rejected("capability_reader_unavailable", 503) from None
