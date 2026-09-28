"""S3 API adapter requiring versioned COMPLIANCE Object Lock retention.

An S3-compatible on-prem endpoint is supported if it implements the same
version listing, per-version retention, and delete-marker semantics. Pass an
authenticated SDK client with a pinned TLS trust root. Storage and signing
identities belong to administrators outside the control-plane database.
"""
from __future__ import annotations

import base64
import hashlib
import json
import re
from datetime import datetime, timedelta, timezone

from .repository import _canonical

_DIGEST = re.compile(r'^[0-9a-f]{64}$')
_SEQUENCE = re.compile(r'^[0-9]{20}\.json$')


class _LockedObjects:
    def __init__(self, client, bucket: str, *, retention_days: int,
                 prefix: str = '', kms_key_id: str | None = None):
        if (client is None or not isinstance(bucket, str) or not bucket
                or type(retention_days) is not int or retention_days < 1
                or not isinstance(prefix, str)
                or (prefix and not re.fullmatch(r'[A-Za-z0-9/_-]+', prefix))
                or (kms_key_id is not None and not kms_key_id)):
            raise ValueError('Object Lock client, bucket and retention are required')
        self.client = client
        self.bucket = bucket
        self.prefix = prefix.strip('/') + '/' if prefix else ''
        self.retention_days = retention_days
        self.kms_key_id = kms_key_id

    def _configured(self) -> None:
        versioning = self.client.get_bucket_versioning(Bucket=self.bucket)
        locking = self.client.get_object_lock_configuration(Bucket=self.bucket)
        if (versioning.get('Status') != 'Enabled' or
                locking.get('ObjectLockConfiguration', {}).get('ObjectLockEnabled') != 'Enabled'):
            raise ValueError('Versioning and Object Lock must be enabled')

    def _versions(self, prefix: str) -> list[dict]:
        self._configured()
        versions: list[dict] = []
        marker = {}
        seen = set()
        while True:
            page = self.client.list_object_versions(Bucket=self.bucket, Prefix=prefix,
                                                    MaxKeys=1000, **marker)
            if page.get('DeleteMarkers'):
                raise ValueError('Object Lock namespace contains a delete marker')
            versions.extend(item for item in page.get('Versions', [])
                            if item['Key'].startswith(prefix))
            if not page.get('IsTruncated'):
                return versions
            marker = {'KeyMarker': page.get('NextKeyMarker'),
                      'VersionIdMarker': page.get('NextVersionIdMarker')}
            if not marker['KeyMarker'] or tuple(marker.values()) in seen:
                raise ValueError('Object Lock version listing cannot advance')
            seen.add(tuple(marker.values()))

    def _bytes(self, key: str, versions: list[dict], max_bytes: int) -> bytes:
        found = [v for v in versions if v['Key'] == key]
        if not found:
            raise FileNotFoundError(key)
        distinct = set()
        now = datetime.now(timezone.utc)
        for version in found:
            version_id = version.get('VersionId')
            if not version_id or version_id == 'null':
                raise ValueError('Object version has no immutable identity')
            retention = self.client.get_object_retention(Bucket=self.bucket,
                                                         Key=key, VersionId=version_id)
            setting = retention.get('Retention', {})
            until = setting.get('RetainUntilDate')
            if (setting.get('Mode') != 'COMPLIANCE' or
                    not isinstance(until, datetime) or not until.tzinfo or until <= now):
                raise ValueError('Object version has no active COMPLIANCE retention')
            response = self.client.get_object(Bucket=self.bucket, Key=key,
                                              VersionId=version_id)
            if response.get('VersionId') != version_id:
                raise ValueError('Object service returned a different version')
            body = response['Body']
            try:
                content = body.read(max_bytes + 1)
            finally:
                body.close()
            if len(content) > max_bytes:
                raise ValueError('Retained object exceeds size limit')
            distinct.add(content)
        if len(distinct) != 1:
            raise ValueError('Retained object versions disagree')
        return distinct.pop()

    def _put(self, key: str, content: bytes, max_bytes: int) -> None:
        if not isinstance(content, bytes) or not 1 <= len(content) <= max_bytes:
            raise ValueError('Invalid retained object content')
        existing = self._versions(key)
        if existing:
            if self._bytes(key, existing, max_bytes) != content:
                raise ValueError('Retained object identity was reused')
            return
        options = {'ServerSideEncryption': 'aws:kms',
                   'SSEKMSKeyId': self.kms_key_id} if self.kms_key_id else {
                   'ServerSideEncryption': 'AES256'}
        response = self.client.put_object(
            Bucket=self.bucket, Key=key, Body=content,
            IfNoneMatch='*',
            ContentType='application/json',
            ContentMD5=base64.b64encode(hashlib.md5(content).digest()).decode('ascii'),
            ObjectLockMode='COMPLIANCE',
            ObjectLockRetainUntilDate=datetime.now(timezone.utc) +
            timedelta(days=self.retention_days), **options)
        if not response.get('VersionId') or response['VersionId'] == 'null':
            raise ValueError('Object Lock service did not return a version identity')
        if self._bytes(key, self._versions(key), max_bytes) != content:
            raise ValueError('Retained object could not be verified')


class S3ObjectLockArtifactStore(_LockedObjects):
    """Content-addressed 1 MiB JSON artifacts in a retained versioned bucket."""

    def _key(self, digest: str) -> str:
        if not isinstance(digest, str) or not _DIGEST.fullmatch(digest):
            raise ValueError('Invalid artifact digest')
        return f'{self.prefix}artifacts/{digest[:2]}/{digest}'

    def put(self, digest: str, content: bytes) -> None:
        if (not isinstance(content, bytes) or not 2 <= len(content) <= 1048576 or
                hashlib.sha256(content).hexdigest() != digest):
            raise ValueError('Artifact digest or size mismatch')
        self._put(self._key(digest), content, 1048576)

    def get(self, digest: str) -> bytes:
        key = self._key(digest)
        content = self._bytes(key, self._versions(key), 1048576)
        if hashlib.sha256(content).hexdigest() != digest:
            raise ValueError('Retained artifact digest mismatch')
        return content


class S3ObjectLockCheckpointStore(_LockedObjects):
    """Independently retained signed checkpoints with a stream namespace."""

    def __init__(self, client, bucket: str, *, stream: str,
                 retention_days: int, prefix: str = '', kms_key_id: str | None = None):
        if stream not in ('evidence_entries', 'audit_events'):
            raise ValueError('Unknown signed checkpoint stream')
        super().__init__(client, bucket, retention_days=retention_days,
                         prefix=prefix, kms_key_id=kms_key_id)
        self.stream = stream

    def _scope(self, organization_id: str, tenant_id: str) -> str:
        scope = (organization_id + '\0' + tenant_id).encode('utf-8')
        return f'{self.prefix}checkpoints/{self.stream}/{hashlib.sha256(scope).hexdigest()}/'

    def latest(self, organization_id: str, tenant_id: str) -> dict | None:
        namespace = self._scope(organization_id, tenant_id)
        versions = self._versions(namespace)
        keys = [v['Key'] for v in versions]
        if any(not _SEQUENCE.fullmatch(key[len(namespace):]) for key in keys):
            raise ValueError('Retained checkpoint namespace has an unexpected key')
        if not keys:
            return None
        return json.loads(self._bytes(max(keys), versions, 8192))

    def publish(self, envelope: dict) -> None:
        payload = envelope['payload']
        sequence = payload['sequence']
        if type(sequence) is not int or sequence < 0:
            raise ValueError('Invalid checkpoint sequence')
        if self.stream == 'audit_events':
            if payload.get('stream') != 'audit_events':
                raise ValueError('Audit checkpoint stream mismatch')
        elif 'stream' in payload:
            raise ValueError('Evidence checkpoint stream mismatch')
        namespace = self._scope(payload['organizationId'], payload['tenantId'])
        latest = self.latest(payload['organizationId'], payload['tenantId'])
        if latest is not None and latest['payload']['sequence'] > sequence:
            raise ValueError('Later retained checkpoint already exists')
        content = _canonical(envelope) + b'\n'
        if len(content) > 8192:
            raise ValueError('Checkpoint envelope exceeds size limit')
        self._put(namespace + f'{sequence:020d}.json', content, 8192)
