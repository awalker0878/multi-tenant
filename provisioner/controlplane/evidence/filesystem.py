"""Single-host durable adapters for a bounded artifact and checkpoint slice.

These paths require independent access controls and retention/backups in a
deployment. A local directory alone is not WORM storage or a separate trust
domain. Never expose these paths or accept them from HTTP request data.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import stat
from pathlib import Path
from uuid import uuid4

_DIGEST = re.compile(r'^[0-9a-f]{64}$')


def _atomic_new(path: Path, content: bytes) -> bool:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    temp = path.parent / ('.tmp-' + uuid4().hex)
    descriptor = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        with os.fdopen(descriptor, 'wb') as output:
            output.write(content)
            output.flush()
            os.fsync(output.fileno())
        try:
            os.link(temp, path, follow_symlinks=False)
            created = True
        except FileExistsError:
            created = False
        directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
        return created
    finally:
        temp.unlink(missing_ok=True)


def _read(path: Path, max_bytes: int) -> bytes:
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(descriptor, 'rb') as source:
        size = os.fstat(source.fileno())
        if not stat.S_ISREG(size.st_mode) or size.st_size > max_bytes:
            raise ValueError('Stored artifact is not a bounded regular file')
        content = source.read(max_bytes + 1)
    if len(content) > max_bytes:
        raise ValueError('Stored artifact exceeds the configured size limit')
    return content


class FileArtifactStore:
    """Atomic create-only SHA-256 blobs; restricted to 1 MiB JSON artifacts."""

    def __init__(self, root: Path):
        self.root = Path(root)

    def _path(self, digest: str) -> Path:
        if not isinstance(digest, str) or not _DIGEST.fullmatch(digest):
            raise ValueError('Invalid content digest')
        return self.root / digest[:2] / digest

    def put(self, digest: str, content: bytes) -> None:
        if (not isinstance(content, bytes) or not 2 <= len(content) <= 1048576
                or hashlib.sha256(content).hexdigest() != digest):
            raise ValueError('Artifact digest or size mismatch')
        path = self._path(digest)
        _atomic_new(path, content)
        if _read(path, 1048576) != content:
            raise ValueError('Stored artifact differs from requested digest')

    def get(self, digest: str) -> bytes:
        content = _read(self._path(digest), 1048576)
        if hashlib.sha256(content).hexdigest() != digest:
            raise ValueError('Stored artifact digest mismatch')
        return content


class FileCheckpointStore:
    """Create-only checkpoint files in a separate operator-controlled root.

    Production must provide retention and administrative independence from
    PostgreSQL and the artifact root. A deleted highest file is not detectable
    by a single unprotected filesystem; see evidence/README.md.
    """

    def __init__(self, root: Path):
        self.root = Path(root)

    def _directory(self, organization_id: str, tenant_id: str) -> Path:
        scope = (organization_id + '\0' + tenant_id).encode('utf-8')
        return self.root / hashlib.sha256(scope).hexdigest()

    def latest(self, organization_id: str, tenant_id: str) -> dict | None:
        directory = self._directory(organization_id, tenant_id)
        try:
            names = [name for name in os.listdir(directory)
                     if re.fullmatch(r'[0-9]{20}\.json', name)]
        except FileNotFoundError:
            return None
        if not names:
            return None
        return json.loads(_read(directory / max(names), 8192))

    def publish(self, envelope: dict) -> None:
        payload = envelope['payload']
        directory = self._directory(payload['organizationId'], payload['tenantId'])
        sequence = payload['sequence']
        if type(sequence) is not int or sequence < 0:
            raise ValueError('Invalid checkpoint sequence')
        latest = self.latest(payload['organizationId'], payload['tenantId'])
        if latest is not None and latest['payload']['sequence'] > sequence:
            raise ValueError('An independently anchored later prefix already exists')
        encoded = (json.dumps(envelope, sort_keys=True, separators=(',', ':'),
                              ensure_ascii=False, allow_nan=False) + '\n').encode('utf-8')
        if len(encoded) > 8192:
            raise ValueError('Checkpoint envelope is too large')
        path = directory / f'{sequence:020d}.json'
        _atomic_new(path, encoded)
        if _read(path, 8192) != encoded:
            raise ValueError('Checkpoint identity was reused with different content')
