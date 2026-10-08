"""Pinned, network-isolated QEMU conversion of a retained migration copy only.

The mounted runtime/rootfs and sandbox executable must match commissioned digests.
No commands/flags come from guest data. Unsupported backing layouts hold rather
than invoking salvage, in-place repair or a second conversion method.
"""

import hashlib
import math
import os
import selectors
import signal
import stat
import subprocess
import sys
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from lifecycle_worker.application.native import NativeHeld, decode, digest, sha256
from lifecycle_worker.infrastructure.native_files import protected_read, sync_directory


def file_digest(path: Path, maximum: int, current: Callable[[], None]) -> dict[str, Any]:
    if not path.is_absolute() or any(p.is_symlink() for p in (path, *path.parents)):
        raise NativeHeld("conversion_path_not_owned")
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, "rb") as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or not 0 < info.st_size <= maximum:
            raise NativeHeld("conversion_file_bound")
        hashes = {name: hashlib.new(name) for name in ("sha256", "sha512")}
        size = 0
        while chunk := stream.read(1048576):
            current()
            size += len(chunk)
            if size > maximum:
                raise NativeHeld("conversion_file_bound")
            for value in hashes.values():
                value.update(chunk)
        if size != info.st_size:
            raise NativeHeld("conversion_file_changed")
        return {"size": size, **{name: value.hexdigest() for name, value in hashes.items()}}


def rootfs_digest(root: Path, current: Callable[[], None]) -> str:
    """Pin all rootfs files/link targets; never follow a rootfs link on the host."""
    if (
        not root.is_absolute()
        or any(p.is_symlink() for p in (root, *root.parents))
        or not root.is_dir()
    ):
        raise NativeHeld("conversion_rootfs_invalid")
    entries: list[list[Any]] = []
    for directory, dirs, files in os.walk(root, followlinks=False):
        for name in sorted(dirs + files):
            current()
            p = Path(directory) / name
            info = p.lstat()
            if len(entries) >= 50000 or (not stat.S_ISLNK(info.st_mode) and info.st_mode & 0o022):
                raise NativeHeld("conversion_rootfs_invalid")
            if stat.S_ISLNK(info.st_mode):
                payload: Any = {"link": os.readlink(p)}
            elif stat.S_ISREG(info.st_mode):
                payload = file_digest(p, 2**31, current)["sha256"]
            elif stat.S_ISDIR(info.st_mode):
                payload = "directory"
            else:
                raise NativeHeld("conversion_rootfs_device_forbidden")
            entries.append([str(p.relative_to(root)), info.st_mode & 0o7777, payload])
    return digest(sorted(entries))


class PinnedQemuSandbox:
    def __init__(self, runtime_file: Path, current: Callable[[], None]) -> None:
        self.runtime = decode(protected_read(runtime_file, 65536))
        if set(self.runtime) != {"sandbox_path", "sandbox_sha256", "rootfs_path", "rootfs_sha256"}:
            raise NativeHeld("conversion_runtime_invalid")
        for key in ("sandbox_sha256", "rootfs_sha256"):
            if not sha256(self.runtime[key]):
                raise NativeHeld("conversion_runtime_invalid")
        self.sandbox, self.rootfs = (
            Path(self.runtime["sandbox_path"]),
            Path(self.runtime["rootfs_path"]),
        )
        if (
            file_digest(self.sandbox, 2**24, current)["sha256"] != self.runtime["sandbox_sha256"]
            or rootfs_digest(self.rootfs, current) != self.runtime["rootfs_sha256"]
        ):
            raise NativeHeld("conversion_runtime_changed")
        if not os.statvfs(self.rootfs).f_flag & os.ST_RDONLY:
            raise NativeHeld("conversion_rootfs_readonly_mount_required")
        qemu = self.rootfs / "usr/bin/qemu-img"
        if not qemu.is_file() or qemu.is_symlink() or not qemu.stat().st_mode & stat.S_IXUSR:
            raise NativeHeld("conversion_qemu_missing")

    @property
    def artifact_sha256(self) -> str:
        return digest(self.runtime)

    def command(self, arguments: list[str], source: Path, output: Path) -> list[str]:
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
            "--ro-bind",
            str(source),
            "/input.img",
            "--bind",
            str(output),
            "/out",
            "--chdir",
            "/out",
            "--",
            "/usr/bin/qemu-img",
            *arguments,
        ]

    def run(
        self,
        arguments: list[str],
        source: Path,
        output: Path,
        max_bytes: int,
        deadline: float,
        current: Callable[[], None],
    ) -> bytes:
        current()
        if file_digest(self.sandbox, 2**24, current)["sha256"] != self.runtime["sandbox_sha256"]:
            raise NativeHeld("conversion_runtime_changed")

        # ASGI invokes this worker in a thread. preexec_fn is unsafe after a
        # multithreaded fork; set limits in a fresh isolated interpreter before
        # replacing it with the pinned sandbox. No shell or guest code is used.
        limiter = (
            "import os,resource,sys; "
            "n=int(sys.argv[1]); "
            "resource.setrlimit(resource.RLIMIT_FSIZE,(n,n)); "
            "resource.setrlimit(resource.RLIMIT_AS,(2**31,2**31)); "
            "c=int(sys.argv[2]); resource.setrlimit(resource.RLIMIT_CPU,(c,c)); "
            "resource.setrlimit(resource.RLIMIT_NOFILE,(64,64)); "
            "resource.setrlimit(resource.RLIMIT_CORE,(0,0)); "
            "os.execv(sys.argv[3],sys.argv[3:])"
        )
        process = subprocess.Popen(
            [
                sys.executable,
                "-I",
                "-S",
                "-c",
                limiter,
                str(max_bytes),
                str(min(86400, max(1, math.ceil(deadline - time.monotonic())))),
                *self.command(arguments, source, output),
            ],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            env={"PATH": "/usr/bin:/bin", "LANG": "C"},
            close_fds=True,
            start_new_session=True,
        )
        data = bytearray()
        try:
            assert process.stdout is not None
            with selectors.DefaultSelector() as selector:
                selector.register(process.stdout, selectors.EVENT_READ)
                while selector.get_map():
                    current()
                    if time.monotonic() >= deadline:
                        raise NativeHeld("conversion_deadline")
                    for key, _ in selector.select(timeout=0.1):
                        chunk = os.read(key.fd, 65536)
                        if not chunk:
                            selector.unregister(key.fileobj)
                            break
                        data.extend(chunk)
                        if len(data) > 65536:
                            raise NativeHeld("conversion_output_bound")
            while process.poll() is None:
                current()
                if time.monotonic() >= deadline:
                    raise NativeHeld("conversion_deadline")
                time.sleep(0.05)
            if process.returncode != 0:
                raise NativeHeld("conversion_engine_held")
            return bytes(data)
        finally:
            # Includes namespace descendants; cancellation is not a successful conversion.
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.wait(timeout=5)
            if process.stdout is not None:
                process.stdout.close()


class CopyConverter:
    def __init__(self, sandbox: PinnedQemuSandbox) -> None:
        self.sandbox = sandbox

    def convert(
        self, source: Path, output: Path, intent: dict[str, Any], current: Callable[[], None]
    ) -> dict[str, Any]:
        if set(intent) != {
            "source_sha256",
            "source_bytes",
            "virtual_bytes",
            "target_format",
            "max_output_bytes",
            "max_seconds",
            "bytes_per_second",
            "artifact_sha256",
        } | ({"source_format"} if "source_format" in intent else set()):
            raise NativeHeld("conversion_intent_invalid")
        if (
            not sha256(intent["source_sha256"])
            or intent["artifact_sha256"] != self.sandbox.artifact_sha256
            or intent["target_format"] not in {"raw", "qcow2", "vmdk"}
            or intent.get("source_format", "vmdk") not in {"raw", "qcow2", "vmdk"}
        ):
            raise NativeHeld("conversion_method_not_qualified")
        for k, low, high in (
            ("source_bytes", 1, 2**46),
            ("virtual_bytes", 512, 2**46),
            ("max_output_bytes", 1, 2**46),
            ("max_seconds", 1, 86400),
            ("bytes_per_second", 65536, 2**34),
        ):
            if type(intent[k]) is not int or not low <= intent[k] <= high:
                raise NativeHeld("conversion_budget_invalid")
        if (
            not output.is_absolute()
            or any(p.is_symlink() for p in (output, *output.parents))
            or source == output
            or output in source.parents
        ):
            raise NativeHeld("conversion_copy_required")
        before = file_digest(source, intent["source_bytes"], current)
        if before["size"] != intent["source_bytes"] or before["sha256"] != intent["source_sha256"]:
            raise NativeHeld("conversion_input_changed")
        output.mkdir(mode=0o700)  # Existing output is retained/held, never overwritten.
        deadline = time.monotonic() + intent["max_seconds"]

        def run(arguments: list[str]) -> bytes:
            return self.sandbox.run(
                arguments, source, output, intent["max_output_bytes"], deadline, current
            )

        source_format = intent.get("source_format", "vmdk")
        info = decode(run(["info", "--output=json", "-f", source_format, "/input.img"]))
        if (
            info.get("format") != source_format
            or type(info.get("virtual-size")) is not int
            or info["virtual-size"] != intent["virtual_bytes"]
            or info.get("backing-filename")
            or info.get("encrypted")
            or info.get("snapshots")
            or info.get("format-specific", {}).get("data", {}).get("data-file")
            or (
                source_format == "vmdk"
                and info.get("format-specific", {}).get("data", {}).get("create-type")
                not in {"streamOptimized", "monolithicSparse"}
            )
        ):
            raise NativeHeld(
                "conversion_vmdk_profile_unqualified"
                if source_format == "vmdk"
                else "conversion_source_profile_unqualified"
            )
        target_format = intent["target_format"]
        target = "/out/disk." + target_format
        run(
            [
                "convert",
                "-f",
                source_format,
                "-O",
                target_format,
                *(["-o", "subformat=streamOptimized"] if target_format == "vmdk" else []),
                "-r",
                str(intent["bytes_per_second"]),
                "/input.img",
                target,
            ]
        )
        converted = decode(run(["info", "--output=json", "-f", target_format, target]))
        if (
            converted.get("format") != target_format
            or type(converted.get("virtual-size")) is not int
            or converted["virtual-size"] != intent["virtual_bytes"]
            or converted.get("backing-filename")
            or converted.get("encrypted")
            or converted.get("snapshots")
            or converted.get("format-specific", {}).get("data", {}).get("data-file")
            or (
                target_format == "vmdk"
                and converted.get("format-specific", {}).get("data", {}).get("create-type")
                != "streamOptimized"
            )
        ):
            raise NativeHeld("conversion_target_metadata_changed")
        if target_format == "qcow2":
            checked = decode(run(["check", "--output=json", "-f", target_format, target]))
            if any(checked.get(k, 0) != 0 for k in ("check-errors", "corruptions", "leaks")):
                raise NativeHeld("conversion_target_corrupt")
        # Compare guest-visible sectors, not storage allocation (which changes by format).
        run(["compare", "-f", source_format, "-F", target_format, "/input.img", target])
        if file_digest(source, intent["source_bytes"], current) != before:
            raise NativeHeld("conversion_input_changed")
        receipt = file_digest(
            output / ("disk." + target_format), intent["max_output_bytes"], current
        )
        descriptor = os.open(
            output / ("disk." + target_format), os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK
        )
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
        sync_directory(output)
        sync_directory(output.parent)
        return {
            **receipt,
            "source_sha256": before["sha256"],
            "virtual_bytes": intent["virtual_bytes"],
            "format": target_format,
            "artifact_sha256": self.sandbox.artifact_sha256,
            "sector_comparison": "passed",
            "guest_transformation": "not_performed",
        }
