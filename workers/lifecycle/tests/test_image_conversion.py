"""Conversion safety/command contracts; synthetic engine, not QEMU qualification."""

import hashlib
import json
from pathlib import Path
from typing import Any

import pytest

from lifecycle_worker.application.native import NativeHeld, digest
from lifecycle_worker.infrastructure.image_conversion import CopyConverter, PinnedQemuSandbox


class Engine(PinnedQemuSandbox):
    def __init__(self) -> None:
        self.runtime = {"fixture": "synthetic-engine"}
        self.calls: list[list[str]] = []
        self.fault = ""
        self.sandbox, self.rootfs = Path("/qualified/bwrap"), Path("/qualified/rootfs")

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
        command = arguments[0]
        if command == "info":
            fmt = arguments[arguments.index("-f") + 1]
            return json.dumps(
                {
                    "format": fmt,
                    "virtual-size": 512,
                    "backing-filename": "/private/key" if self.fault == "backing" else None,
                    "format-specific": {
                        "data": {
                            "create-type": "splitSparse"
                            if self.fault == "subtype"
                            else "streamOptimized"
                        }
                    },
                }
            ).encode()
        if command == "convert":
            fmt = arguments[arguments.index("-O") + 1]
            (output / ("disk." + fmt)).write_bytes(b"synthetic-converted" * 20)
            if self.fault == "source_change":
                source.write_bytes(b"changed")
            if self.fault == "lost":
                raise NativeHeld("conversion_engine_held")
        if command == "check":
            return json.dumps({"corruptions": 1 if self.fault == "corrupt" else 0}).encode()
        if command == "compare" and self.fault == "sector_mismatch":
            raise NativeHeld("conversion_engine_held")
        return b""


@pytest.fixture
def intent(tmp_path: Path) -> tuple[Path, Path, dict[str, Any], Engine]:
    source = tmp_path / "source.vmdk"
    source.write_bytes(b"synthetic-vmdk")
    engine = Engine()
    p = {
        "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "source_bytes": source.stat().st_size,
        "virtual_bytes": 512,
        "target_format": "qcow2",
        "max_output_bytes": 1048576,
        "max_seconds": 30,
        "bytes_per_second": 1048576,
        "artifact_sha256": engine.artifact_sha256,
    }
    return source, tmp_path / "converted", p, engine


def test_conversion_is_new_copy_checked_and_sector_compared(intent: Any) -> None:
    source, output, p, engine = intent
    original = source.read_bytes()
    receipt = CopyConverter(engine).convert(source, output, p, lambda: None)
    assert source.read_bytes() == original
    assert [c[0] for c in engine.calls] == ["info", "convert", "info", "check", "compare"]
    assert receipt["sector_comparison"] == "passed"
    assert receipt["guest_transformation"] == "not_performed"
    assert receipt["sha256"] == hashlib.sha256((output / "disk.qcow2").read_bytes()).hexdigest()
    assert not any(
        flag in {"--salvage", "-U", "--force-share", "rebase", "commit"}
        for c in engine.calls
        for flag in c
    )


@pytest.mark.parametrize(
    "fault", ["backing", "subtype", "corrupt", "sector_mismatch", "source_change", "lost"]
)
def test_conversion_failure_has_no_fallback_or_inplace_repair(intent: Any, fault: str) -> None:
    source, output, p, engine = intent
    engine.fault = fault
    with pytest.raises(NativeHeld):
        CopyConverter(engine).convert(source, output, p, lambda: None)
    assert sum(c[0] == "convert" for c in engine.calls) <= 1
    with pytest.raises((NativeHeld, FileExistsError)):
        CopyConverter(engine).convert(source, output, p, lambda: None)
    assert sum(c[0] == "convert" for c in engine.calls) <= 1


@pytest.mark.parametrize(
    "fault", ["digest", "artifact", "format", "budget", "symlink", "overwrite"]
)
def test_unsafe_conversion_request_never_executes(intent: Any, fault: str) -> None:
    source, output, p, engine = intent
    if fault == "digest":
        p["source_sha256"] = digest("wrong")
    if fault == "artifact":
        p["artifact_sha256"] = digest("wrong")
    if fault == "format":
        p["target_format"] = "automatic"
    if fault == "budget":
        p["max_seconds"] = True
    if fault == "symlink":
        link = source.parent / "link.vmdk"
        link.symlink_to(source)
        source = link
    if fault == "overwrite":
        output.mkdir()
    with pytest.raises((NativeHeld, FileExistsError)):
        CopyConverter(engine).convert(source, output, p, lambda: None)
    assert engine.calls == []


def test_sandbox_has_no_network_credentials_or_writable_source() -> None:
    command = Engine().command(
        ["info", "/input.vmdk"], Path("/custody/source.vmdk"), Path("/custody/result")
    )
    assert "--unshare-all" in command and "--clearenv" in command and "--cap-drop" in command
    assert command[command.index("/custody/source.vmdk") - 1] == "--ro-bind"
    assert command.count("--bind") == 1
    assert "--share-net" not in command and "--share-user" not in command
