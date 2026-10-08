"""Synthetic guest appliance exercises real copy custody and fail-closed inspection."""

import hashlib
import time
from pathlib import Path
from typing import Any

import pytest

from lifecycle_worker.application.native import NativeHeld
from lifecycle_worker.infrastructure.guest_preparation import GuestPreparation, PinnedGuestSandbox
from lifecycle_worker.infrastructure.image_conversion import file_digest


class Appliance(PinnedGuestSandbox):
    def __init__(self, root: Path) -> None:
        self.rootfs = root
        self.runtime = {"fixture": "synthetic-guest-appliance"}
        self.calls: list[list[str]] = []
        self.fault = ""

    def run(
        self,
        arguments: list[str],
        source: Path,
        output: Path,
        max_bytes: int,
        deadline: float,
        current: Any,
    ) -> bytes:
        current()
        self.calls.append(arguments)
        if self.fault == "lost":
            raise NativeHeld("guest_interrupted")
        if arguments[0] == "virt-inspector":
            return (
                "<operatingsystems><operatingsystem><name>"
                + ("windows" if self.fault == "os" else "linux")
                + "</name>"
                "<distro>ubuntu</distro><arch>x86_64</arch><major_version>24</major_version>"
                "</operatingsystem></operatingsystems>"
            ).encode()
        assert "--no-network" in arguments
        assert sum(a == "-a" for a in arguments) == 2
        for key in ("root", "data"):
            p = output / key / "disk.raw"
            p.write_bytes(b"p" * p.stat().st_size)
        return b""


def setup(tmp_path: Path) -> tuple[Appliance, dict[str, Any], Path, dict[str, Any]]:
    root = tmp_path / "rootfs"
    profiles = root / "usr/share/migration/profiles"
    profiles.mkdir(parents=True)
    commands = b"run /usr/share/migration/profiles/linux-kvm.sh\n"
    (profiles / "linux-kvm.txt").write_bytes(commands)
    appliance = Appliance(root)
    selected = {
        "id": "linux-kvm",
        "family": "linux",
        "distribution": "ubuntu",
        "major_version": 24,
        "architecture": "x86_64",
        "firmware": "efi",
        "target_platform": "ahv",
        "commands_sha256": hashlib.sha256(commands).hexdigest(),
        "artifact_sha256": appliance.artifact_sha256,
    }
    directory = tmp_path / "copy"
    directory.mkdir(mode=0o700)
    disks = {}
    for key in ("root", "data"):
        (directory / key).mkdir(mode=0o700)
        path = directory / key / "disk.raw"
        path.write_bytes(b"a" * 1024)
        disks[key] = file_digest(path, 1024, lambda: None) | {"format": "raw"}
    return appliance, selected, directory, disks


def test_prepares_all_private_copies_and_retains_before_after_integrity(tmp_path: Path) -> None:
    appliance, selected, directory, disks = setup(tmp_path)
    result = GuestPreparation(appliance).prepare(
        directory, disks, selected, time.monotonic() + 30, lambda: None
    )
    assert result["input_sha256"] != result["output_sha256"]
    assert set(result["disks"]) == {"root", "data"}
    assert result["boot_verified"] is False and result["application_ready"] is False
    assert [a[0] for a in appliance.calls] == ["virt-inspector", "virt-customize", "virt-inspector"]


@pytest.mark.parametrize("fault", ["os", "lost", "profile", "artifact", "path", "digest", "format"])
def test_unknown_or_unowned_guest_copy_never_completes(tmp_path: Path, fault: str) -> None:
    appliance, selected, directory, disks = setup(tmp_path)
    if fault in {"os", "lost"}:
        appliance.fault = fault
    if fault == "profile":
        selected["commands_sha256"] = "a" * 64
    if fault == "artifact":
        selected["artifact_sha256"] = "b" * 64
    if fault == "path":
        directory.chmod(0o755)
    if fault == "digest":
        disks["root"]["sha256"] = "c" * 64
    if fault == "format":
        disks["root"]["format"] = "qcow2"
    with pytest.raises(NativeHeld):
        GuestPreparation(appliance).prepare(
            directory, disks, selected, time.monotonic() + 30, lambda: None
        )
    assert not any(a[0] == "virt-customize" for a in appliance.calls)


def test_hardlinked_disk_cannot_modify_source_custody(tmp_path: Path) -> None:
    appliance, selected, directory, disks = setup(tmp_path)
    source = tmp_path / "immutable-source.raw"
    disk = directory / "root" / "disk.raw"
    source.hardlink_to(disk)
    before = source.read_bytes()
    with pytest.raises(NativeHeld, match="guest_private_copy_required"):
        GuestPreparation(appliance).prepare(
            directory, disks, selected, time.monotonic() + 30, lambda: None
        )
    assert source.read_bytes() == before and not appliance.calls
