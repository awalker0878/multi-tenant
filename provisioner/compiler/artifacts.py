"""Artifact rendering and private output storage.

Generated inputs are written exactly once, outside the repository, with private
permissions. A second render of the same decision must produce byte-identical
content; a difference is a determinism defect, not a new artifact.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from provisioner.domain.errors import ProvisioningError
from provisioner.domain.request import canonical_json, digest
from provisioner.repository import ROOT

ARTIFACT_FORMAT = 'hosting-provisioning-artifacts/1'
MANIFEST = 'manifest.json'


def render(value) -> str:
    """One canonical, newline-terminated rendering of an artifact."""
    return canonical_json(value) + '\n'


def assert_deterministic(name: str, value) -> str:
    """Return the artifact digest, refusing content that renders inconsistently."""
    first = render(value)
    second = render(value)
    if first != second:
        raise ProvisioningError('DETERMINISM_VIOLATION',
                                f'Artifact {name} does not render deterministically',
                                path=f'artifacts.{name}')
    return digest(value)


def assert_output_path(path: Path) -> Path:
    path = Path(path)
    if path.resolve().is_relative_to(ROOT):
        raise ProvisioningError('OUTPUT_PATH_NOT_PRIVATE',
                                'Generated inputs must be written outside the repository',
                                path=str(path), details={'repository_root': str(ROOT)})
    if path.exists():
        raise ProvisioningError('OUTPUT_PATH_NOT_PRIVATE',
                                'Refusing to overwrite an existing generated input set',
                                path=str(path))
    return path


def write(directory: Path, artifacts: dict[str, object]) -> dict:
    """Write every artifact into a new private directory and return its manifest."""
    directory = assert_output_path(directory)
    digests = {name: assert_deterministic(name, value) for name, value in sorted(artifacts.items())}
    manifest = {'format': ARTIFACT_FORMAT, 'status': 'WRITTEN_DISABLED_NOT_AUTHORIZED',
                'artifacts': digests,
                'combined_digest': digest(digests),
                'native_contact': False,
                'limits': ['Generated inputs are disabled and carry no production authorization',
                           'A generated input set is immutable; regenerate into a new directory']}
    directory.mkdir(mode=0o700, parents=False, exist_ok=False)
    for name, value in sorted(artifacts.items()):
        path = directory / name
        path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        with open(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), 'w',
                  encoding='utf-8') as stream:
            stream.write(render(value))
    with open(os.open(directory / MANIFEST, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), 'w',
              encoding='utf-8') as stream:
        json.dump(manifest, stream, indent=2, sort_keys=True)
        stream.write('\n')
    return manifest