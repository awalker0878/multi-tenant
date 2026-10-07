"""Separately mounted, revocable observation grants; no browser-selected secret paths."""

import hmac
import os
import re
import stat
import time
from pathlib import Path
from typing import Any

from lifecycle.domain.execution import Rejected, decode, identity
from lifecycle.domain.native_workflow import exact, integer


def protected(path: str, maximum: int) -> bytes:
    location = Path(path)
    if not location.is_absolute() or any(p.is_symlink() for p in [location, *location.parents]):
        raise ValueError
    descriptor = os.open(location, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(descriptor, "rb") as stream:
        mode = os.fstat(stream.fileno()).st_mode
        if not stat.S_ISREG(mode) or mode & 0o022:
            raise ValueError
        raw = stream.read(maximum + 1)
        if len(raw) > maximum:
            raise ValueError
        return raw


class CampaignObservers:
    def authorize(self, token: str, tenant: str, kind: str, value: dict[str, Any]) -> str:
        try:
            registry = decode(protected(os.environ["LIFECYCLE_CAMPAIGN_OBSERVERS_FILE"], 262144))
            exact(registry, {"schema_version", "grants"})
            if type(registry["schema_version"]) is not int or registry["schema_version"] != 1:
                raise ValueError
            grants = registry["grants"]
            if not isinstance(grants, list) or not 1 <= len(grants) <= 256:
                raise ValueError
            matches = []
            tokens = []
            for grant in grants:
                exact(
                    grant,
                    {"tenant_id", "observer_id", "token_file", "expires_at", "kind", "resources"},
                )
                identity(grant["tenant_id"])
                identity(grant["observer_id"])
                integer(grant["expires_at"])
                resources = grant["resources"]
                if (
                    grant["kind"] not in {"performance", "capacity", "release"}
                    or not isinstance(resources, list)
                    or not 1 <= len(resources) <= 256
                    or not all(isinstance(r, str) for r in resources)
                ):
                    raise ValueError
                credential = protected(grant["token_file"], 4096).decode().rstrip("\r\n")
                if not re.fullmatch(r"[A-Za-z0-9_-]{32,4096}", credential):
                    raise ValueError
                tokens.append(credential)
                if hmac.compare_digest(token, credential):
                    matches.append(grant)
            # A capacity reader cannot accidentally use a worker's credential.
            if len(set(tokens)) != len(tokens) or len(matches) != 1:
                raise Rejected("observation_caller_denied", 401)
            grant = matches[0]
            resource = value.get("route_sha256" if kind == "performance" else "pool_key")
            if (
                grant["tenant_id"] != tenant
                or grant["kind"] != kind
                or grant["expires_at"] <= time.time()
                or resource not in grant["resources"]
            ):
                raise Rejected("observation_scope_denied", 403)
            return str(grant["observer_id"])
        except Rejected:
            raise
        except (KeyError, TypeError, ValueError, OSError, UnicodeError):
            raise Rejected("observation_authority_unavailable", 503) from None
