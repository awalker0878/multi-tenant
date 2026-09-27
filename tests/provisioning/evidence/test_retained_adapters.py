"""Fault injection against on-prem S3 API retention and Vault Transit ports."""
from __future__ import annotations

import base64
import hashlib
import io
import json
import unittest
from datetime import datetime, timedelta, timezone

from provisioner.controlplane.evidence import (S3ObjectLockArtifactStore,
                                               S3ObjectLockCheckpointStore,
                                               VaultTransitSigner,
                                               VaultTransitVerifier)


class FakeObjectLock:
    def __init__(self):
        self.objects = {}
        self.markers = []
        self.locked = True
        self.versioning = True

    def get_bucket_versioning(self, **kwargs):
        return {'Status': 'Enabled' if self.versioning else 'Suspended'}

    def get_object_lock_configuration(self, **kwargs):
        return {'ObjectLockConfiguration': {'ObjectLockEnabled':
                'Enabled' if self.locked else 'Disabled'}}

    def list_object_versions(self, *, Prefix, **kwargs):
        versions = [{'Key': key, 'VersionId': version_id}
                    for key, items in self.objects.items() if key.startswith(Prefix)
                    for version_id, *_ in items]
        return {'Versions': versions, 'DeleteMarkers': [marker for marker in self.markers
                if marker['Key'].startswith(Prefix)], 'IsTruncated': False}

    def put_object(self, *, Key, Body, ObjectLockMode,
                   ObjectLockRetainUntilDate, **kwargs):
        if kwargs.get('IfNoneMatch') != '*':
            raise ValueError('Create-only conditional write required')
        if Key in self.objects:
            raise ValueError('Conditional object write rejected')
        version_id = str(sum(map(len, self.objects.values())) + 1)
        self.objects.setdefault(Key, []).append(
            (version_id, Body, ObjectLockMode, ObjectLockRetainUntilDate))
        return {'VersionId': version_id}

    def get_object_retention(self, *, Key, VersionId, **kwargs):
        item = next(item for item in self.objects[Key] if item[0] == VersionId)
        return {'Retention': {'Mode': item[2], 'RetainUntilDate': item[3]}}

    def get_object(self, *, Key, VersionId, **kwargs):
        item = next(item for item in self.objects[Key] if item[0] == VersionId)
        return {'VersionId': VersionId, 'Body': io.BytesIO(item[1])}


class FakeTransit:
    def __init__(self):
        self.calls = []

    def post(self, mount, operation, key, payload):
        self.calls.append((mount, operation, key, payload))
        if operation == 'sign':
            return {'signature': 'vault:v1:' + base64.b64encode(
                hashlib.sha256(base64.b64decode(payload['input'])).digest()).decode()}
        expected = 'vault:v1:' + base64.b64encode(
            hashlib.sha256(base64.b64decode(payload['input'])).digest()).decode()
        return {'valid': payload['signature'] == expected}


class RetainedAdapterTests(unittest.TestCase):
    def test_artifact_requires_all_versions_retained_and_equal(self):
        service = FakeObjectLock()
        store = S3ObjectLockArtifactStore(service, 'evidence-bucket', retention_days=365)
        content = b'{"result":"PASS"}'
        digest = hashlib.sha256(content).hexdigest()
        store.put(digest, content)
        self.assertEqual(store.get(digest), content)
        store.put(digest, content)
        key = store._key(digest)
        first = service.objects[key][0]
        service.objects[key].append(('new-version', b'{"result":"FAIL"}', 'COMPLIANCE',
                                     first[3]))
        with self.assertRaises(ValueError):
            store.get(digest)
        service.objects[key].pop()
        service.objects[key][0] = (first[0], first[1], 'GOVERNANCE', first[3])
        with self.assertRaises(ValueError):
            store.get(digest)
        service.objects[key][0] = (first[0], first[1], 'COMPLIANCE',
                                   datetime.now(timezone.utc) - timedelta(seconds=1))
        with self.assertRaises(ValueError):
            store.get(digest)

    def test_checkpoint_detects_marker_and_rejects_rollback_and_missing_lock(self):
        service = FakeObjectLock()
        store = S3ObjectLockCheckpointStore(service, 'audit-bucket',
                                            stream='audit_events', retention_days=365)
        def envelope(sequence):
            return {'payload': {'stream': 'audit_events', 'organizationId': 'org',
                                'tenantId': 'tenant', 'sequence': sequence},
                    'signature': 'test'}
        store.publish(envelope(0))
        store.publish(envelope(1))
        self.assertEqual(store.latest('org', 'tenant'), envelope(1))
        with self.assertRaises(ValueError):
            store.publish(envelope(0))
        service.markers.append({'Key': store._scope('org', 'tenant') +
                               '00000000000000000001.json'})
        with self.assertRaises(ValueError):
            store.latest('org', 'tenant')
        service.markers.clear()
        service.locked = False
        with self.assertRaises(ValueError):
            store.latest('org', 'tenant')

    def test_vault_transit_sign_verify_and_revocation(self):
        service = FakeTransit()
        signer = VaultTransitSigner(service, key_id='evidence-2026',
                                    mount='transit', key='checkpoint')
        verifier = VaultTransitVerifier(service,
                                        {'evidence-2026': ('transit', 'checkpoint')})
        signature = signer.sign(b'{"head":"abc"}')
        verifier.verify(signer.key_id, b'{"head":"abc"}', signature)
        self.assertEqual(service.calls[0][1], 'sign')
        self.assertEqual(service.calls[1][1], 'verify')
        with self.assertRaises(ValueError):
            verifier.verify(signer.key_id, b'tampered', signature)
        with self.assertRaises(ValueError):
            verifier.verify('revoked-key', b'{"head":"abc"}', signature)


if __name__ == '__main__':
    unittest.main()
