"""Content-addressed evidence with externally signed high-water checkpoints."""

from .repository import (Checkpoint, EvidenceConflict, EvidenceEntry,
                         EvidenceIntegrityError, EvidenceRepository,
                         EvidenceUnavailable, Verification)
from .filesystem import FileArtifactStore, FileCheckpointStore
from .audit import AuditCheckpointRepository, AuditVerification
from .object_lock import S3ObjectLockArtifactStore, S3ObjectLockCheckpointStore
from .vault import VaultTransitClient, VaultTransitSigner, VaultTransitVerifier

__all__ = [
    'Checkpoint', 'EvidenceConflict', 'EvidenceEntry',
    'EvidenceIntegrityError', 'EvidenceRepository', 'EvidenceUnavailable',
    'FileArtifactStore', 'FileCheckpointStore', 'Verification',
    'AuditCheckpointRepository', 'AuditVerification',
    'S3ObjectLockArtifactStore', 'S3ObjectLockCheckpointStore',
    'VaultTransitClient', 'VaultTransitSigner', 'VaultTransitVerifier',
]
