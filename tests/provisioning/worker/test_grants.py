"""Worker grant shapes and broker trust boundary without native credentials."""
from __future__ import annotations

import unittest
from dataclasses import replace
from datetime import datetime, timedelta, timezone

from provisioner.controlplane.authority.model import PlanScope
from provisioner.controlplane.persistence import TenantContext
from provisioner.controlplane.worker import (CredentialBroker, GrantDenied,
                                             GrantRequest, PostgresWorkerGrants,
                                             VerifiedWorkerIdentity)


class Verifier:
    def __init__(self, identity):
        self.identity = identity

    def verify(self, evidence):
        if evidence != 'verified-mtls-peer':
            raise GrantDenied('No authenticated mTLS peer')
        return self.identity


class Grants:
    def __init__(self):
        self.called = False

    def with_authorized_reference(self, context, identity, grant_id, *, use, **operation):
        self.called = True
        return use('vault-ref-only', object(), identity.expires_at)


class Issuer:
    def __init__(self):
        self.called = False

    def issue(self, reference, *, grant, expires_at):
        self.called = True
        assert reference == 'vault-ref-only'
        return object()


class WorkerBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.scope = PlanScope('org-01', 'tenant-01', 'site-01', 'wsd-01',
                               'endpoint-01', 'native-01', 'vmware')
        self.identity = VerifiedWorkerIdentity(
            'org-01', 'tenant-01', 'worker-01', 'site-01', 'a' * 64,
            datetime.now(timezone.utc) + timedelta(hours=1))
        self.request = GrantRequest('job-01', 'step-01', 'operation-01',
                                    'VM_POWER', self.scope, 'lease-01', 2,
                                    timedelta(minutes=2))

    def test_exact_request_and_certificate_validation(self):
        with self.assertRaises(ValueError):
            replace(self.request, operation_kind='SHELL_EXEC')
        with self.assertRaises(ValueError):
            replace(self.request, ttl=timedelta(minutes=6))
        with self.assertRaises(ValueError):
            replace(self.request, lease_epoch=0)
        with self.assertRaises(ValueError):
            replace(self.identity, certificate_sha256='not-a-fingerprint')

    def test_missing_lease_authority_is_fail_closed(self):
        with self.assertRaises(ValueError):
            PostgresWorkerGrants(lambda: None, None)

    def test_broker_requires_independent_identity_before_issuer(self):
        grants, issuer = Grants(), Issuer()
        broker = CredentialBroker(Verifier(self.identity), grants, issuer)
        with self.assertRaises(GrantDenied):
            broker.acquire('unverified-header', TenantContext('org-01', 'tenant-01'),
                           'grant-01', job_id='job-01', step_id='step-01',
                           operation_id='operation-01', operation_kind='VM_POWER',
                           operation_scope=self.scope, lease_key='lease-01',
                           lease_epoch=2)
        self.assertFalse(grants.called)
        self.assertFalse(issuer.called)
        handle = broker.acquire('verified-mtls-peer', TenantContext('org-01', 'tenant-01'),
                                'grant-01', job_id='job-01', step_id='step-01',
                                operation_id='operation-01', operation_kind='VM_POWER',
                                operation_scope=self.scope, lease_key='lease-01',
                                lease_epoch=2)
        self.assertIsNotNone(handle)
        self.assertTrue(issuer.called)


if __name__ == '__main__':
    unittest.main()
