"""Restricted exact-byte originals using the existing COMPLIANCE custody owner."""
from provisioner.controlplane.evidence.object_lock import _LockedObjects
from provisioner.execution import readback_core as c
from provisioner.execution.run_files import digest, require
from .rehearsal import MAX_FILE_BYTES


class RetainedOriginalStore(_LockedObjects):
    """Separate restricted/KMS bucket; never the sanitized evidence namespace."""

    def __init__(self, client, bucket: str, *, retention_days: int,
                 prefix: str, kms_key_id: str):
        require(kms_key_id and prefix, 'Separate protected originals namespace and KMS key required')
        super().__init__(client, bucket, retention_days=retention_days,
                         prefix=prefix, kms_key_id=kms_key_id)

    def _key(self, expected):
        require(isinstance(expected, str) and c.HEX.fullmatch(expected), 'Original digest required')
        return self.prefix + 'originals/' + expected[:2] + '/' + expected

    def retain(self, expected: str, raw: bytes) -> None:
        require(isinstance(raw, bytes) and len(raw) <= MAX_FILE_BYTES and
                digest(raw) == expected, 'Original bytes, digest or size differ')
        content = b'hosting-retained-original/1\n' + str(len(raw)).encode('ascii') + b'\n' + raw
        self._put(self._key(expected), content, MAX_FILE_BYTES + 64)
        self.require(expected, raw)

    def require(self, expected: str, raw: bytes) -> None:
        require(self.read(expected) == raw, 'Original immutable versions/retention differ')

    def read(self, expected: str) -> bytes:
        key = self._key(expected)
        retained = self._bytes(key, self._versions(key), MAX_FILE_BYTES + 64)
        try:
            marker, extent, raw = retained.split(b'\n', 2)
        except ValueError as exc:
            raise ValueError('Original container is incomplete') from exc
        require(marker == b'hosting-retained-original/1' and extent == str(len(raw)).encode('ascii')
                and len(raw) <= MAX_FILE_BYTES and digest(raw) == expected,
                'Original immutable container, extent or digest differs')
        return raw
