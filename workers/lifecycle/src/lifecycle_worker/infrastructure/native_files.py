"""Bounded no-follow reads and exact artifact inventory for native worker inputs."""

import hashlib
import os
import stat
from pathlib import Path, PurePosixPath
from typing import Any

from lifecycle_worker.application.native import NativeHeld, decode, digest, sha256


def protected_read(path: Path, limit: int) -> bytes:
    if not path.is_absolute() or limit < 1:
        raise NativeHeld("protected_absolute_file_required")
    # Reject symlinks in every path component, not just the final component.
    for part in (path, *path.parents):
        if part.is_symlink():
            raise NativeHeld("symlink_native_input")
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(fd, "rb") as handle:
            info = os.fstat(handle.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_size > limit or info.st_mode & 0o022:
                raise NativeHeld("unsafe_native_file")
            raw = handle.read(limit + 1)
            if len(raw) > limit:
                raise NativeHeld("oversized_native_file")
            return raw
    except OSError:
        raise NativeHeld("native_file_unavailable") from None


def relative_file(root: Path, name: Any) -> Path:
    if (
        not isinstance(name, str)
        or not name
        or "\\" in name
        or any(ord(c) < 32 for c in name)
        or PurePosixPath(name).is_absolute()
        or any(p in {"", ".", ".."} for p in name.split("/"))
    ):
        raise NativeHeld("invalid_bundle_path")
    return root / name


def verify_bundle(root: Path, expected_digest: str) -> dict[str, Any]:
    manifest = decode(protected_read(root / "bundle.json", 1_048_576))
    if digest(manifest) != expected_digest:
        raise NativeHeld("native_bundle_changed")
    if (
        set(manifest)
        != {
            "schema_version",
            "terraform_version",
            "terraform_sha256",
            "saved_plan",
            "plan_json_sha256",
            "files",
            "resources",
            "environment_sha256",
        }
        or type(manifest["schema_version"]) is not int
        or manifest["schema_version"] != 1
    ):
        raise NativeHeld("invalid_native_bundle")
    files = manifest["files"]
    if (
        not isinstance(files, dict)
        or not 1 <= len(files) <= 4096
        or "bundle.json" in files
        or manifest["saved_plan"] not in files
        or ".terraform.lock.hcl" not in files
        or not all(
            sha256(manifest[k])
            for k in (
                "terraform_sha256",
                "plan_json_sha256",
                "environment_sha256",
            )
        )
    ):
        raise NativeHeld("incomplete_native_bundle")
    inventory = list(root.rglob("*"))
    if any(p.is_symlink() for p in inventory):
        raise NativeHeld("symlink_native_input")
    actual = {p.relative_to(root).as_posix() for p in inventory if not p.is_dir()}
    if actual != set(files) | {"bundle.json"}:
        raise NativeHeld("unlisted_native_artifact")
    for name, expected in files.items():
        path = relative_file(root, name)
        if (
            not sha256(expected)
            or hashlib.sha256(protected_read(path, 536_870_912)).hexdigest() != expected
        ):
            raise NativeHeld("native_artifact_changed")
    return manifest
