"""Current Linux kernel controls for one isolated restic worker.

The worker is commissioned in a dedicated cgroup and a bounded staging volume.
This reader never creates either. It refuses a normal shared filesystem, an
unlimited block device, or a controller that has escaped its enrolled cgroup.
These controls bound block I/O, rather than cached filesystem operations.
"""
from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import re

from provisioner.execution.run_files import private_path, require


@dataclass(frozen=True)
class TransferLimits:
    download_kib_per_second: int
    block_iops: int
    stage_bytes: int
    expected_bytes: int

    def __post_init__(self):
        require(all(type(value) is int and value > 0 for value in
                    (self.download_kib_per_second, self.block_iops, self.stage_bytes))
                and type(self.expected_bytes) is int
                and 0 < self.expected_bytes <= self.stage_bytes,
                'Positive immutable transfer limits and known useful bytes required')
        require(self.download_kib_per_second <= 1024 * 1024
                and self.block_iops <= 1000000 and self.stage_bytes <= 2 ** 60,
                'Transfer limits exceed the supported bounded range')

    def to_dict(self):
        return dict(download_kib_per_second=self.download_kib_per_second,
                    block_iops=self.block_iops, stage_bytes=self.stage_bytes,
                    expected_bytes=self.expected_bytes)


@dataclass(frozen=True)
class LinuxTransferResources:
    """Trusted process-local configuration supplied by the enrolled worker.

    The immutable job pins ``binding()`` independently. A packet cannot enroll
    a cgroup or manufacture a mount by carrying these paths. The fixed system
    paths are deliberately not injectable production inputs.
    """
    stage_parent: Path
    cgroup: str
    block_device: str
    limits: TransferLimits

    def __post_init__(self):
        require(isinstance(self.stage_parent, Path)
                and self.stage_parent.is_absolute()
                and self.stage_parent != Path('/')
                and '..' not in self.stage_parent.parts
                and str(self.stage_parent) == os.path.normpath(str(self.stage_parent)),
                'Canonical independently commissioned staging parent required')
        require(isinstance(self.cgroup, str)
                and re.fullmatch(r'/[A-Za-z0-9_.:@/-]+', self.cgroup)
                and '..' not in Path(self.cgroup).parts and self.cgroup != '/',
                'Exact dedicated cgroup required')
        require(isinstance(self.block_device, str)
                and re.fullmatch(r'[0-9]+:[0-9]+', self.block_device)
                and isinstance(self.limits, TransferLimits),
                'Exact local staging block device and transfer limits required')

    def binding(self):
        return dict(stage_parent=str(self.stage_parent), cgroup=self.cgroup,
                    block_device=self.block_device, limits=self.limits.to_dict())

    def require_target(self, target):
        path = Path(target)
        require(path.is_absolute() and path.parent == self.stage_parent
                and str(path) == os.path.normpath(str(path)),
                'One new direct child of the commissioned staging volume required')
        self.require_current()

    def require_current(self):
        parent = private_path(self.stage_parent, directory=True)
        device = parent.stat().st_dev
        require(self.block_device == f'{os.major(device)}:{os.minor(device)}'
                and Path('/sys/dev/block', self.block_device).exists(),
                'Staging must use the exact commissioned local block device')
        # A dedicated mount's physical ceiling is enforced by the filesystem.
        # A shared larger volume with a caller-declared budget is not equivalent.
        require(os.path.ismount(parent), 'Staging parent must be a dedicated mount')
        space = os.statvfs(parent)
        isolation_flags = os.ST_NOSUID | os.ST_NODEV | os.ST_NOEXEC
        require(space.f_flag & isolation_flags == isolation_flags,
                'Staging must enforce nosuid, nodev and noexec before restore')
        require(space.f_frsize > 0
                and space.f_blocks * space.f_frsize <= self.limits.stage_bytes,
                'Staging filesystem exceeds the immutable hard byte ceiling')
        require(Path('/proc/self/cgroup').read_text().splitlines() ==
                ['0::' + self.cgroup], 'Worker escaped its commissioned unified cgroup')
        control = Path('/sys/fs/cgroup') / self.cgroup.lstrip('/')
        require(not any(p.is_symlink() for p in (control, *control.parents)),
                'Cgroup control path cannot contain links')
        require((control / 'cgroup.type').read_text().strip() == 'domain'
                and 'io' in (control.parent / 'cgroup.subtree_control').read_text().split(),
                'A delegated domain with the kernel I/O controller is required')
        rows = [line.split() for line in (control / 'io.max').read_text().splitlines()]
        rows = [row for row in rows if row and row[0] == self.block_device]
        require(len(rows) == 1, 'One enforced staging-device I/O limit is required')
        settings = {}
        for field in rows[0][1:]:
            key, separator, raw = field.partition('=')
            require(separator and key not in settings and raw.isdecimal(),
                    'Unlimited, duplicate or malformed kernel I/O controls are refused')
            settings[key] = int(raw)
        expected = dict(rbps=self.limits.download_kib_per_second * 1024,
                        wbps=self.limits.download_kib_per_second * 1024,
                        riops=self.limits.block_iops, wiops=self.limits.block_iops)
        require(set(settings) == set(expected)
                and all(0 < settings[key] <= value for key, value in expected.items()),
                'Kernel block bandwidth or IOPS exceeds the immutable job limits')
        return self.binding()

    def require_capacity(self, metadata_bytes):
        self.require_current()
        require(type(metadata_bytes) is int and metadata_bytes >= 0,
                'Exact retained manifest byte count required')
        space = os.statvfs(self.stage_parent)
        require((self.limits.expected_bytes + metadata_bytes) <=
                space.f_bavail * space.f_frsize,
                'Staging has insufficient currently available space')
