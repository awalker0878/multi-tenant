"""Fixed offline image inspection/conversion in mandatory Linux namespaces.

Only reviewed qemu-img info/convert are exposed. No shell, network, inherited
credentials, device passthrough, backing-file chain or unconfined fallback exists.
This owner converts a retained standalone disk; it neither captures a running VM
nor imports/boots a guest nor qualifies whole-VM mobility.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
from tempfile import TemporaryFile
from dataclasses import dataclass
from typing import Callable

from provisioner.execution.run_files import private_path

_SHA = re.compile(r'^[0-9a-f]{64}$')
_FORMATS = {'raw', 'qcow2', 'vmdk', 'vdi'}


class ImageSandboxHold(RuntimeError):
    """Input, mandatory isolation or reviewed converter could not be proven."""


def _digest(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1048576), b''):
            digest.update(chunk)
    return digest.hexdigest()


@dataclass(frozen=True)
class SandboxToolchain:
    bwrap: Path
    qemu_img: Path
    prlimit: Path
    bwrap_sha256: str
    qemu_img_sha256: str
    prlimit_sha256: str

    def verify(self) -> None:
        for path, expected in ((self.bwrap, self.bwrap_sha256),
                               (self.qemu_img, self.qemu_img_sha256),
                               (self.prlimit, self.prlimit_sha256)):
            if (not isinstance(path, Path) or not path.is_absolute()
                    or not isinstance(expected, str) or not _SHA.fullmatch(expected)):
                raise ImageSandboxHold('Exact reviewed tool paths and digests required')
            try:
                real = path.resolve(strict=True)
                info = real.stat()
                if (not real.is_relative_to(Path('/usr')) or not stat.S_ISREG(info.st_mode)
                        or info.st_mode & 0o022 or info.st_uid != 0
                        or not info.st_mode & 0o111 or _digest(real) != expected):
                    raise ImageSandboxHold('Installed converter differs from reviewed toolchain')
            except OSError:
                raise ImageSandboxHold('Mandatory sandbox/conversion tool is unavailable') from None


@dataclass(frozen=True)
class ImageLimits:
    max_input_bytes: int
    max_virtual_bytes: int
    memory_bytes: int = 2147483648
    cpu_seconds: int = 900
    wall_seconds: int = 1800

    def __post_init__(self):
        if (any(type(value) is not int for value in vars(self).values())
                or not 1 <= self.max_input_bytes <= 64 * 1024**4
                or not 1 <= self.max_virtual_bytes <= 64 * 1024**4
                or not 268435456 <= self.memory_bytes <= 64 * 1024**3
                or not 1 <= self.cpu_seconds <= 86400
                or not self.cpu_seconds <= self.wall_seconds <= 172800):
            raise ValueError('Bounded image conversion budgets required')


def _argv(tools: SandboxToolchain, staging: Path, output: Path,
          limits: ImageLimits, qemu_arguments: list[str]) -> list[str]:
    # /usr and library trees contain only the site-reviewed converter runtime.
    # No /etc, /home, sockets, devices, source directories or secret mounts.
    output_limit = 65536 if qemu_arguments[0] == 'info' else limits.max_virtual_bytes + 16 * 1024**2
    argv = [str(tools.prlimit), '--as=' + str(limits.memory_bytes),
            '--fsize=' + str(output_limit),
            '--cpu=' + str(limits.cpu_seconds), '--nofile=64', '--',
            str(tools.bwrap), '--unshare-all', '--die-with-parent', '--new-session',
            '--cap-drop', 'ALL', '--clearenv', '--ro-bind', '/usr', '/usr']
    for library in ('/lib', '/lib64'):
        if Path(library).exists():
            argv += ['--ro-bind', library, library]
    argv += ['--ro-bind', str(staging), '/input', '--bind', str(output), '/output',
             '--proc', '/proc', '--dev', '/dev', '--size', '16777216', '--tmpfs', '/tmp',
             '--chdir', '/output', '--', str(tools.qemu_img), *qemu_arguments]
    return argv


def _run(tools: SandboxToolchain, staging: Path, output: Path, limits: ImageLimits,
         arguments: list[str], runner: Callable) -> bytes:
    tools.verify()
    try:
        with TemporaryFile() as stdout, TemporaryFile() as stderr:
            runner(_argv(tools, staging, output, limits, arguments),
                   env={'PATH': '/usr/bin'}, stdin=subprocess.DEVNULL,
                   stdout=stdout, stderr=stderr,
                   timeout=limits.wall_seconds, check=True)
            stdout.seek(0)
            result = stdout.read(65537)
    except (OSError, subprocess.SubprocessError):
        raise ImageSandboxHold('Mandatory namespace/resource isolation or fixed converter failed') from None
    if not isinstance(result, bytes) or len(result) > 65536:
        raise ImageSandboxHold('Converter returned unbounded metadata')
    return result


def _inspection(raw: bytes, input_format: str, limits: ImageLimits) -> dict:
    try:
        value = json.loads(raw)
    except (ValueError, UnicodeError):
        raise ImageSandboxHold('Converter returned invalid metadata') from None
    if (not isinstance(value, dict) or value.get('format') != input_format
            or type(value.get('virtual-size')) is not int
            or not 1 <= value['virtual-size'] <= limits.max_virtual_bytes
            or value.get('backing-filename') or value.get('full-backing-filename')
            or value.get('encrypted') is True
            or 'encrypt' in json.dumps(value.get('format-specific', {})).lower()):
        raise ImageSandboxHold('Unknown format, backing chain, encryption or virtual size is unsupported')
    return {'format': input_format, 'virtualSize': value['virtual-size']}


def _request(source_sha256, input_format, tools, limits):
    if (not isinstance(source_sha256, str) or not _SHA.fullmatch(source_sha256)
            or input_format not in _FORMATS or not isinstance(limits, ImageLimits)
            or not isinstance(tools, SandboxToolchain)):
        raise ImageSandboxHold('Retained input digest, explicit format and reviewed isolation required')
    tools.verify()


def _retain_input(source: Path, destination: Path, limits: ImageLimits):
    """Seal one bounded standalone input before any isolated metadata parser."""
    source, destination = Path(source), Path(destination)
    try:
        private_path(destination.parent, directory=True)
    except (OSError, ValueError):
        raise ImageSandboxHold('Conversion output requires independently protected private storage') from None
    descriptor = os.open(source, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        info = os.fstat(descriptor)
        if (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1
                or info.st_size < 1 or info.st_size > limits.max_input_bytes):
            raise ImageSandboxHold('Source must be one bounded standalone regular disk image')
        if destination.exists() or destination.is_symlink():
            raise ImageSandboxHold('Conversion destination must be new and private')
        destination.mkdir(parents=False, mode=0o700)
        staging = destination / 'retained-input'
        output = destination / 'converted'
        staging.mkdir(mode=0o700)
        output.mkdir(mode=0o700)
        retained = staging / 'disk.image'
        with os.fdopen(descriptor, 'rb', closefd=False) as stream, retained.open('xb') as target:
            os.chmod(retained, 0o400)
            copied = 0
            while True:
                chunk = stream.read(min(1048576, info.st_size - copied + 1))
                if not chunk:
                    break
                if copied + len(chunk) > info.st_size:
                    raise ImageSandboxHold('Input grew beyond its retained byte budget during capture')
                target.write(chunk)
                copied += len(chunk)
            if copied != info.st_size:
                raise ImageSandboxHold('Input size changed during retained capture')
            target.flush()
            os.fsync(target.fileno())
    finally:
        os.close(descriptor)
    return staging, output, retained


def inspect(source: Path, destination: Path, *, source_sha256: str,
            input_format: str, tools: SandboxToolchain, limits: ImageLimits,
            runner: Callable = subprocess.run) -> dict:
    """Inspect a retained standalone disk; no convert, capture, import or boot."""
    _request(source_sha256, input_format, tools, limits)
    staging, output, retained = _retain_input(source, destination, limits)
    if _digest(retained) != source_sha256:
        raise ImageSandboxHold('Retained disk bytes differ from immutable capture digest')
    metadata = _inspection(_run(tools, staging, output, limits,
        ['info', '--output=json', '-f', input_format, '/input/disk.image'], runner), input_format, limits)
    if _digest(retained) != source_sha256:
        raise ImageSandboxHold('Retained immutable input changed during isolated inspection')
    return {'format': 'hosting-isolated-disk-inspection/1',
            'status': 'RETAINED_DISK_INSPECTED_NOT_CAPTURE_OR_GUEST_QUALIFICATION',
            'sourceSha256': source_sha256, 'inputFormat': input_format,
            'virtualSize': metadata['virtualSize'], 'inputBytes': retained.stat().st_size,
            'toolchain': {name: getattr(tools, name) for name in (
                'bwrap_sha256', 'qemu_img_sha256', 'prlimit_sha256')},
            'nativeContact': False, 'mutationAuthorized': False, 'guestBootQualified': False}


def convert(source: Path, destination: Path, *, source_sha256: str,
            input_format: str, tools: SandboxToolchain, limits: ImageLimits,
            runner: Callable = subprocess.run) -> dict:
    """Inspect and convert a standalone cold disk into a fresh private QCOW2 artifact."""
    _request(source_sha256, input_format, tools, limits)
    staging, output, retained = _retain_input(source, destination, limits)
    if _digest(retained) != source_sha256:
        raise ImageSandboxHold('Retained disk bytes differ from immutable capture digest')
    metadata = _inspection(_run(tools, staging, output, limits,
        ['info', '--output=json', '-f', input_format, '/input/disk.image'], runner), input_format, limits)
    _run(tools, staging, output, limits,
         ['convert', '-f', input_format, '-O', 'qcow2', '/input/disk.image', '/output/disk.qcow2'], runner)
    result_path = output / 'disk.qcow2'
    info = result_path.lstat()
    if (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1
            or not 1 <= info.st_size <= limits.max_virtual_bytes + 16 * 1024**2
            or _digest(retained) != source_sha256):
        raise ImageSandboxHold('Converted output or retained immutable input is invalid')
    os.chmod(result_path, 0o400)
    # Reinspect inside the same mandatory sandbox. No imported/boot success claim.
    converted = _inspection(_run(tools, staging, output, limits,
        ['info', '--output=json', '-f', 'qcow2', '/output/disk.qcow2'], runner), 'qcow2', limits)
    if converted['virtualSize'] != metadata['virtualSize']:
        raise ImageSandboxHold('Converted virtual disk extent differs from retained source')
    return {'format': 'hosting-isolated-disk-conversion/1',
            'status': 'CONVERTED_DISK_ARTIFACT_NOT_GUEST_QUALIFICATION',
            'sourceSha256': source_sha256, 'outputSha256': _digest(result_path),
            'inputFormat': input_format, 'outputFormat': 'qcow2',
            'virtualSize': converted['virtualSize'], 'outputBytes': info.st_size,
            'toolchain': {name: getattr(tools, name) for name in (
                'bwrap_sha256', 'qemu_img_sha256', 'prlimit_sha256')},
            'outputPath': str(result_path), 'nativeContact': False,
            'mutationAuthorized': False, 'guestBootQualified': False}
