"""Offline guest preparation on private, sector-verified RAW copies only.

The sealed appliance includes virt-customize, virt-inspector, approved offline
packages/drivers and the selected command profile. The host executes no guest
shell. A prepared filesystem does not establish successful boot or service health.
"""

import os
import re
import stat
import xml.etree.ElementTree as ET
from collections.abc import Callable
from pathlib import Path
from typing import Any

from lifecycle_worker.application.api_plan import shape
from lifecycle_worker.application.native import NativeHeld, digest, sha256
from lifecycle_worker.infrastructure.image_conversion import PinnedQemuSandbox, file_digest
from lifecycle_worker.infrastructure.native_files import protected_read


def profile(value: Any) -> dict[str, Any]:
    shape(
        value,
        {
            "id",
            "family",
            "distribution",
            "major_version",
            "architecture",
            "target_platform",
            "firmware",
            "commands_sha256",
            "artifact_sha256",
        },
    )
    p: dict[str, Any] = value
    if (
        not isinstance(p["id"], str)
        or not re.fullmatch(r"[a-z0-9_-]{1,80}", p["id"])
        or p["family"] not in {"linux", "windows"}
        or p["target_platform"] not in {"vmware", "openstack", "ahv"}
        or p["firmware"] not in {"bios", "efi"}
        or p["architecture"] != "x86_64"
        or type(p["major_version"]) is not int
        or not 1 <= p["major_version"] <= 9999
        or not isinstance(p["distribution"], str)
        or not re.fullmatch(r"[a-z0-9_-]{1,80}", p["distribution"])
        or not sha256(p["commands_sha256"])
        or not sha256(p["artifact_sha256"])
    ):
        raise NativeHeld("guest_profile_not_selected")
    return p


class PinnedGuestSandbox(PinnedQemuSandbox):
    def __init__(self, runtime_file: Path, current: Callable[[], None]) -> None:
        super().__init__(runtime_file, current)
        for executable in ("virt-customize", "virt-inspector"):
            path = self.rootfs / "usr/bin" / executable
            if not path.is_file() or path.is_symlink() or not path.stat().st_mode & 0o100:
                raise NativeHeld("guest_appliance_missing")

    def command(self, arguments: list[str], source: Path, output: Path) -> list[str]:
        if arguments[0] not in {"virt-customize", "virt-inspector"}:
            raise NativeHeld("guest_tool_not_allowed")
        # QEMU TCG inside the appliance: no host /dev/kvm, network, credentials,
        # source disk, or uncontrolled profile mount is exposed to guest tools.
        return [
            str(self.sandbox),
            "--unshare-all",
            "--die-with-parent",
            "--new-session",
            "--cap-drop",
            "ALL",
            "--clearenv",
            "--ro-bind",
            str(self.rootfs),
            "/",
            "--proc",
            "/proc",
            "--dev",
            "/dev",
            "--tmpfs",
            "/tmp",
            "--tmpfs",
            "/run",
            "--setenv",
            "LIBGUESTFS_BACKEND",
            "direct",
            "--setenv",
            "LIBGUESTFS_BACKEND_SETTINGS",
            "force_tcg",
            "--setenv",
            "PATH",
            "/usr/bin:/bin",
            "--bind",
            str(output),
            "/out",
            "--chdir",
            "/out",
            "--",
            "/usr/bin/" + arguments[0],
            *arguments[1:],
        ]


class GuestPreparation:
    def __init__(self, sandbox: PinnedGuestSandbox) -> None:
        self.sandbox = sandbox

    def validate(self, selected: dict[str, Any]) -> None:
        p = profile(selected)
        path = self.sandbox.rootfs / "usr/share/migration/profiles" / (p["id"] + ".txt")
        import hashlib

        if (
            p["artifact_sha256"] != self.sandbox.artifact_sha256
            or hashlib.sha256(protected_read(path, 65536)).hexdigest() != p["commands_sha256"]
        ):
            raise NativeHeld("guest_profile_artifact_changed")

    def prepare(
        self,
        directory: Path,
        disks: dict[str, dict[str, Any]],
        selected: dict[str, Any],
        deadline: float,
        current: Callable[[], None],
    ) -> dict[str, Any]:
        self.validate(selected)
        if (
            not directory.is_absolute()
            or not directory.is_dir()
            or any(p.is_symlink() for p in (directory, *directory.parents))
            or directory.stat().st_mode & 0o077
            or not 1 <= len(disks) <= 32
        ):
            raise NativeHeld("guest_private_copy_required")
        arguments = []
        before = {}
        for key, disk in disks.items():
            if not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", key) or disk.get("format") != "raw":
                raise NativeHeld("guest_raw_copy_required")
            path = directory / key / "disk.raw"
            # A hard link into source custody would turn an offline transform
            # into an in-place source edit. Only isolated writable inodes qualify.
            if (
                not stat.S_ISREG(path.lstat().st_mode)
                or path.stat().st_nlink != 1
                or path.parent.stat().st_mode & 0o077
            ):
                raise NativeHeld("guest_private_copy_required")
            observed = file_digest(path, disk["size"], current)
            if any(observed[k] != disk[k] for k in ("size", "sha256", "sha512")):
                raise NativeHeld("guest_copy_integrity_changed")
            before[key] = observed
            arguments += ["--format", "raw", "-a", "/out/" + key + "/disk.raw"]

        def run(args: list[str]) -> bytes:
            current()
            return self.sandbox.run(
                args,
                directory,
                directory,
                max(d["size"] for d in disks.values()),
                deadline,
                current,
            )

        def inspect() -> str:
            raw = run(["virt-inspector", *arguments])
            if b"<!DOCTYPE" in raw.upper() or b"<!ENTITY" in raw.upper():
                raise NativeHeld("guest_inspection_invalid")
            try:
                roots = ET.fromstring(raw).findall("operatingsystem")
            except ET.ParseError:
                raise NativeHeld("guest_inspection_invalid") from None
            if len(roots) != 1:
                raise NativeHeld("guest_multiboot_unqualified")
            observed = {
                k: roots[0].findtext(k) for k in ("name", "distro", "arch", "major_version")
            }
            expected = {
                "name": selected["family"],
                "distro": selected["distribution"],
                "arch": selected["architecture"],
                "major_version": str(selected["major_version"]),
            }
            if observed != expected:
                raise NativeHeld("guest_os_profile_changed")
            return digest(observed)

        inspected = inspect()
        run(
            [
                "virt-customize",
                "--no-network",
                *arguments,
                "--commands-from-file",
                "/usr/share/migration/profiles/" + selected["id"] + ".txt",
            ]
        )
        if inspect() != inspected:
            raise NativeHeld("guest_identity_changed")
        after = {
            key: file_digest(directory / key / "disk.raw", disk["size"], current)
            for key, disk in disks.items()
        }
        if any(after[k]["size"] != before[k]["size"] for k in disks):
            raise NativeHeld("guest_capacity_changed")
        for key in disks:
            path = directory / key / "disk.raw"
            descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
            try:
                if os.fstat(descriptor).st_nlink != 1:
                    raise NativeHeld("guest_private_copy_required")
                os.fsync(descriptor)
            finally:
                os.close(descriptor)
        return {
            "profile_sha256": digest(selected),
            "input_sha256": digest(before),
            "output_sha256": digest(after),
            "inspection_sha256": inspected,
            "disks": after,
            "boot_verified": False,
            "application_ready": False,
        }
