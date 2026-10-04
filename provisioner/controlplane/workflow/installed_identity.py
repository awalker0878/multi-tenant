"""Read the actual sealed installation before commissioning a native worker.

An environment digest, Python version label or success receipt alone cannot
identify the running artifact. The fixed build owner rehashes the accepted
wheel, installed tree and current source closure, including the interpreter.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import sys

from provisioner.execution import runtime_build
from provisioner.execution.run_files import digest, load_private, private_path, read_private, require
from provisioner.execution.source_integrity import verify, verify_runtime


@dataclass(frozen=True)
class InstalledApplicationIdentity:
    configuration_path: Path = field(repr=False)
    source_root: Path = field(repr=False)
    configuration_sha256: str
    source_commit: str
    artifact_sha256: str

    def __post_init__(self):
        require(isinstance(self.configuration_path, Path) and isinstance(self.source_root, Path),
                'Actual protected runtime configuration and current source root required')
        self.require_current()

    @classmethod
    def from_configuration(cls, path: Path, source_root: Path):
        selected = private_path(path)
        raw = read_private(selected)
        config = load_private(selected)
        runtime_build.validate(config, source_root)
        application = [row for row in config['wheels'] if row['name'] == 'hosting-provisioner']
        require(len(application) == 1, 'The exact accepted application wheel is required')
        return cls(selected, source_root, digest(raw), config['source_commit'], application[0]['sha256'])

    def require_current(self):
        require(digest(read_private(self.configuration_path)) == self.configuration_sha256,
                'The original sealed runtime configuration changed')
        config = load_private(self.configuration_path)
        runtime_build.validate(config, self.source_root)
        require(config['source_commit'] == self.source_commit,
                'The actual installation selected another source revision')
        source = verify(self.source_root)
        require(source['status'] == 'HASHES_MATCH' and source['commit'] == self.source_commit
                and verify_runtime(self.source_root)['status'] == 'RUNTIME_SOURCES_MATCH',
                'The actual installed application source differs from the selected commit')
        output = private_path(Path(config['output']), directory=True)
        require(Path(sys.executable).absolute() == output / 'env/bin/python',
                'The service is not running its exact sealed installed interpreter')
        # Reuse the actual build validators, including wheel-to-source and
        # every installed file/mode. This never installs or repairs a runtime.
        runtime_build.artifacts(config, self.source_root)
        receipt = runtime_build.validate_receipt(config, output)
        application = [row for row in config['wheels'] if row['name'] == 'hosting-provisioner']
        require(len(application) == 1 and application[0]['sha256'] == self.artifact_sha256
                and receipt['source_commit'] == self.source_commit,
                'The actual accepted application artifact or sealed runtime changed')
        return self.source_commit, self.artifact_sha256
