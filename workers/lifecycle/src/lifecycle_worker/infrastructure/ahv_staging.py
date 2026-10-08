"""Private, expiring HTTPS grants for converted disks. No browser supplied URLs."""

import asyncio
import ipaddress
import json
import os
import re
import secrets
import stat
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from lifecycle_worker.application.native import NativeBinding, NativeHeld, decode
from lifecycle_worker.infrastructure.image_conversion import file_digest
from lifecycle_worker.infrastructure.native_files import protected_read


def private_directory(path: Path) -> None:
    if (
        not path.is_absolute()
        or not path.is_dir()
        or path.stat().st_mode & 0o077
        or any(p.is_symlink() for p in (path, *path.parents))
    ):
        raise NativeHeld("private_ahv_staging_required")


class AhvStaging:
    def __init__(
        self,
        root: Path,
        spool: Path,
        origin: str,
        clock: Callable[[], int] = lambda: int(time.time()),
    ) -> None:
        u = urlsplit(origin)
        if (
            u.scheme != "https"
            or not u.hostname
            or u.username
            or u.password
            or u.query
            or u.fragment
            or u.path not in {"", "/"}
            or "\\" in origin
        ):
            raise NativeHeld("private_https_staging_required")
        private_directory(root)
        private_directory(spool)
        self.root, self.spool, self.origin, self.clock = root, spool, origin.rstrip("/"), clock

    def grant(self, binding: NativeBinding, path: Path, receipt: dict[str, Any]) -> tuple[str, str]:
        if self.clock() >= binding.expires_at or not path.is_relative_to(self.spool):
            raise NativeHeld("invalid_ahv_staging_scope")
        private_directory(self.root)
        token = secrets.token_hex(32)
        value = {
            "binding_sha256": binding.fingerprint,
            "path": str(path.relative_to(self.spool)),
            "expires_at": binding.expires_at,
            **{k: receipt[k] for k in ("size", "sha256", "sha512")},
        }
        fd = os.open(self.root / (token + ".json"), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w") as handle:
            json.dump(value, handle, allow_nan=False)
            handle.flush()
            os.fsync(handle.fileno())
        return self.origin + "/ahv-artifacts/" + token, token

    def revoke(self, token: str) -> None:
        if re.fullmatch(r"[a-f0-9]{64}", token) is None:
            raise NativeHeld("invalid_ahv_grant")
        (self.root / (token + ".json")).unlink(missing_ok=True)


class AhvArtifactApp:
    def __init__(self, staging: AhvStaging, addresses: list[str]) -> None:
        if not addresses or len(addresses) > 64:
            raise NativeHeld("ahv_staging_readers_required")
        self.staging = staging
        self.addresses = {str(ipaddress.ip_address(a)) for a in addresses}

    async def __call__(self, scope: dict[str, Any], receive: Any, send: Any) -> None:
        token = scope.get("path", "").removeprefix("/ahv-artifacts/")
        started = False
        try:
            if (
                scope.get("type") != "http"
                or scope.get("method") not in {"GET", "HEAD"}
                or scope.get("scheme") != "https"
                or scope.get("query_string")
                or (scope.get("client") or [None])[0] not in self.addresses
                or re.fullmatch(r"[a-f0-9]{64}", token) is None
                or scope.get("path") != "/ahv-artifacts/" + token
            ):
                raise NativeHeld("ahv_artifact_denied")
            grant_path = self.staging.root / (token + ".json")
            raw = protected_read(grant_path, 4096)
            grant = decode(raw)
            relative = Path(grant["path"])
            if relative.is_absolute() or any(p in {"..", "."} for p in relative.parts):
                raise NativeHeld("ahv_artifact_denied")
            path = self.staging.spool / relative

            def current() -> None:
                if (
                    self.staging.clock() >= grant["expires_at"]
                    or protected_read(grant_path, 4096) != raw
                ):
                    raise NativeHeld("ahv_artifact_revoked")

            current()
            # Verify custody before sending bytes; no arbitrary file/URL forwarding.
            hashes = await asyncio.to_thread(file_digest, path, grant["size"], current)
            if any(hashes[k] != grant[k] for k in ("size", "sha256", "sha512")):
                raise NativeHeld("ahv_artifact_changed")
            fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
            with os.fdopen(fd, "rb") as handle:
                info = os.fstat(handle.fileno())
                if not stat.S_ISREG(info.st_mode) or info.st_size != grant["size"]:
                    raise NativeHeld("ahv_artifact_changed")
                current()
                await send(
                    {
                        "type": "http.response.start",
                        "status": 200,
                        "headers": [
                            (b"content-type", b"application/octet-stream"),
                            (b"content-length", str(grant["size"]).encode()),
                            (b"cache-control", b"no-store"),
                            (b"x-content-type-options", b"nosniff"),
                        ],
                    }
                )
                started = True
                remaining = 0 if scope["method"] == "HEAD" else grant["size"]
                while remaining:
                    current()
                    chunk = handle.read(min(1048576, remaining))
                    if not chunk or os.fstat(handle.fileno()) != info:
                        raise NativeHeld("ahv_artifact_changed")
                    remaining -= len(chunk)
                    await send({"type": "http.response.body", "body": chunk, "more_body": True})
                await send({"type": "http.response.body", "body": b"", "more_body": False})
        except Exception:
            if started:
                # Abort an interrupted transfer; never report a successful short body.
                raise NativeHeld("ahv_artifact_transfer_interrupted") from None
            await send({"type": "http.response.start", "status": 404, "headers": []})
            await send({"type": "http.response.body", "body": b""})
