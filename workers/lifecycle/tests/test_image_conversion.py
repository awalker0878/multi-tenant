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


@pytest.mark.parametrize("source_format", ["raw", "qcow2", "vmdk"])
@pytest.mark.parametrize("target_format", ["raw", "qcow2", "vmdk"])
def test_explicit_formats_use_readonly_source_and_sector_equivalence(
    intent: Any, source_format: str, target_format: str
) -> None:
    source, output, p, engine = intent
    p.update(source_format=source_format, target_format=target_format)
    original = source.read_bytes()
    receipt = CopyConverter(engine).convert(source, output, p, lambda: None)
    assert receipt["format"] == target_format and source.read_bytes() == original
    assert engine.calls[0] == ["info", "--output=json", "-f", source_format, "/input.img"]
    assert engine.calls[-1] == [
        "compare",
        "-f",
        source_format,
        "-F",
        target_format,
        "/input.img",
        "/out/disk." + target_format,
    ]
    convert = next(c for c in engine.calls if c[0] == "convert")
    assert ("subformat=streamOptimized" in convert) == (target_format == "vmdk")


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
        ["info", "/input.img"], Path("/custody/source.vmdk"), Path("/custody/result")
    )
    assert "--unshare-all" in command and "--clearenv" in command and "--cap-drop" in command
    assert command[command.index("/custody/source.vmdk") - 1] == "--ro-bind"
    assert command.count("--bind") == 1
    assert "--share-net" not in command and "--share-user" not in command


@pytest.mark.parametrize("fault", ["file_bound", "output_bound", "deadline"])
def test_real_subprocess_limits_and_threaded_cancellation(tmp_path: Path, fault: str) -> None:
    import sys
    import time
    from concurrent.futures import ThreadPoolExecutor

    class ProcessEngine(PinnedQemuSandbox):
        def __init__(self) -> None:
            # This fixture exercises the real launcher, not a QEMU/bubblewrap runtime.
            self.sandbox = tmp_path / "synthetic-sandbox"
            self.sandbox.write_bytes(b"synthetic launcher artifact")
            self.runtime = {"sandbox_sha256": hashlib.sha256(self.sandbox.read_bytes()).hexdigest()}

        def command(self, arguments: list[str], source: Path, output: Path) -> list[str]:
            return [sys.executable, "-I", "-S", "-c", arguments[0]]

    output = tmp_path / "partial"
    code = {
        "file_bound": f"f=open({str(output)!r},'wb'); f.write(b'x'*4096); f.flush()",
        "output_bound": "import sys; sys.stdout.write('x'*131072)",
        "deadline": "import time; time.sleep(5)",
    }[fault]
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(
            ProcessEngine().run,
            [code],
            tmp_path,
            tmp_path,
            1024,
            time.monotonic() + 0.5,
            lambda: None,
        )
        reason = {
            "file_bound": "conversion_engine_held",
            "output_bound": "conversion_output_bound",
            "deadline": "conversion_deadline",
        }[fault]
        with pytest.raises(NativeHeld, match=reason):
            future.result(timeout=3)
    if fault == "file_bound":
        assert output.stat().st_size <= 1024
