"""Pinned JWKS and independent role/session enrollment tests."""
from __future__ import annotations

import json
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa

from provisioner.controlplane.authority.model import PlanScope, PortfolioScope, RoleGrant
from provisioner.controlplane.authority.oidc import DirectoryIdentity, OIDCIdentityProvider
from provisioner.controlplane.authority.service import AuthenticationFailed

ISSUER = 'https://login.example.test/realm'
AUDIENCE = 'urn:hosting:controlplane'
JWKS_URI = 'https://login.example.test/realm/keys'


class Directory:
    def __init__(self, enrollment):
        self.enrollment = enrollment
        self.lookups = []

    def resolve(self, issuer, subject, session_id):
        self.lookups.append((issuer, subject, session_id))
        return self.enrollment


class OIDCTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.private_a = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        cls.private_b = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        cls.private_rogue = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    def setUp(self):
        self.now = datetime.now(timezone.utc).replace(microsecond=0)
        self.scope = PlanScope('org-a', 'tenant-a', 'site-a', 'wsd-a', 'endpoint-a', 'native-a', 'nutanix')
        self.role = RoleGrant('SOURCE_OWNER', self.scope, self.now + timedelta(hours=1))
        self.directory = Directory(DirectoryIdentity(
            'user-a', 'session-a', 'org-a', 'tenant-a', 'HUMAN', True, (self.role,)))
        self.keys = [self.jwk(self.private_a, 'key-a')]
        self.fetches = []
        self.provider = self.make_provider()

    @staticmethod
    def jwk(private_key, kid):
        key = json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(private_key.public_key()))
        key.update({'kid': kid, 'alg': 'RS256', 'use': 'sig', 'key_ops': ['verify']})
        return key

    def make_provider(self, **overrides):
        def fetch(url):
            self.fetches.append(url)
            return {'keys': self.keys}

        settings = dict(issuer=ISSUER, audience=AUDIENCE, jwks_uri=JWKS_URI,
                        directory=self.directory, step_up_acr=frozenset({'urn:gc:loa:step-up'}),
                        fetch_jwks=fetch)
        settings.update(overrides)
        return OIDCIdentityProvider(**settings)

    def token(self, *, private_key=None, kid='key-a', headers=None, **claims):
        payload = dict(iss=ISSUER, aud=AUDIENCE, sub='user-a', sid='session-a',
                       iat=int(self.now.timestamp()), nbf=int(self.now.timestamp()),
                       exp=int((self.now + timedelta(minutes=10)).timestamp()))
        payload.update(claims)
        return jwt.encode(payload, private_key or self.private_a, algorithm='RS256',
                          headers={'kid': kid, 'typ': 'at+jwt', **(headers or {})})

    def assert_rejected(self, token):
        with self.assertRaises(AuthenticationFailed):
            self.provider.authenticate(token)

    def test_verified_token_resolves_exact_live_session_and_directory_scopes(self):
        token = self.token(organizationId='forged-org', tenantId='forged-tenant',
                           roles=['DESTINATION_OWNER'])
        principal = self.provider.authenticate(token)
        self.assertEqual((principal.subject, principal.organization_id,
                          principal.tenant_id, principal.kind),
                         ('user-a', 'org-a', 'tenant-a', 'HUMAN'))
        self.assertEqual(principal.grants, (self.role,))
        self.assertIsNone(principal.step_up_at)
        self.assertEqual(self.directory.lookups, [(ISSUER, 'user-a', 'session-a')])
        self.assertEqual(self.fetches, [JWKS_URI])

    def test_step_up_comes_from_configured_acr_and_verified_auth_time(self):
        auth_time = self.now - timedelta(minutes=1)
        principal = self.provider.authenticate(self.token(
            acr='urn:gc:loa:step-up', auth_time=int(auth_time.timestamp())))
        self.assertEqual(principal.step_up_at, auth_time)
        self.assertIsNone(self.provider.authenticate(self.token(
            acr='urn:gc:loa:other', auth_time=int(auth_time.timestamp()))).step_up_at)
        self.assert_rejected(self.token(acr='urn:gc:loa:step-up'))
        self.assert_rejected(self.token(acr='urn:gc:loa:step-up', auth_time='yesterday'))
        self.assert_rejected(self.token(acr='urn:gc:loa:step-up',
                                        auth_time=int((self.now + timedelta(minutes=1)).timestamp())))

    def test_session_revocation_is_checked_on_every_authentication(self):
        token = self.token()
        self.provider.authenticate(token)
        self.directory.enrollment = DirectoryIdentity(
            'user-a', 'session-a', 'org-a', 'tenant-a', 'HUMAN', False, (self.role,))
        self.assert_rejected(token)
        self.assertEqual(len(self.directory.lookups), 2)

    def test_directory_subject_session_and_scope_cannot_cross_boundaries(self):
        for identity in (
            DirectoryIdentity('someone-else', 'session-a', 'org-a', 'tenant-a', 'HUMAN', True, (self.role,)),
            DirectoryIdentity('user-a', 'other-session', 'org-a', 'tenant-a', 'HUMAN', True, (self.role,)),
            DirectoryIdentity('user-a', 'session-a', 'org-b', 'tenant-a', 'HUMAN', True, (self.role,)),
            DirectoryIdentity('user-a', 'session-a', 'org-a', 'tenant-b', 'HUMAN', True, (self.role,)),
        ):
            with self.subTest(identity=identity):
                self.directory.enrollment = identity
                self.assert_rejected(self.token())

    def test_portfolio_role_is_accepted_from_directory_only(self):
        scoped = RoleGrant('WORKLOAD_READER', PortfolioScope('org-a', 'tenant-a', 'wsd-a'),
                           self.now + timedelta(minutes=10))
        self.directory.enrollment = DirectoryIdentity(
            'user-a', 'session-a', 'org-a', 'tenant-a', 'HUMAN', True, (scoped,))
        principal = self.provider.authenticate(self.token(roles=['SOURCE_OWNER']))
        self.assertEqual(principal.grants, (scoped,))

    def test_issuer_audience_and_signature_are_exact(self):
        self.assert_rejected(self.token(iss='https://another.example.test/realm'))
        self.assert_rejected(self.token(aud='urn:some-other-api'))
        self.assert_rejected(self.token(aud=[AUDIENCE, 'urn:extra']))
        self.assert_rejected(self.token(private_key=self.private_rogue))

    def test_expiry_not_before_issued_at_and_max_age_fail_closed(self):
        self.assert_rejected(self.token(exp=int((self.now - timedelta(seconds=1)).timestamp())))
        self.assert_rejected(self.token(nbf=int((self.now + timedelta(minutes=1)).timestamp())))
        self.assert_rejected(self.token(iat=int((self.now + timedelta(minutes=1)).timestamp())))
        self.assert_rejected(self.token(iat=int((self.now - timedelta(minutes=16)).timestamp())))
        self.assert_rejected(self.token(iat=True))
        self.assert_rejected(self.token(exp='not-a-timestamp'))
        self.assert_rejected(self.token(exp=int((self.now - timedelta(minutes=1)).timestamp()),
                                        iat=int(self.now.timestamp())))

    def test_missing_session_and_untrusted_credentials_fail_closed(self):
        self.assert_rejected(self.token(sid=None))
        self.assert_rejected(self.token(sid=123))
        self.assert_rejected({'jwt': self.token(), 'roles': ['SOURCE_OWNER']})
        self.assert_rejected('Bearer ' + self.token())

    def test_algorithm_token_type_and_unknown_critical_header_are_rejected(self):
        self.assert_rejected(self.token(headers={'typ': 'JWT'}))
        self.assert_rejected(self.token(headers={'typ': 'application/id+jwt'}))
        self.assert_rejected(self.token(headers={'crit': ['unknown']}))
        self.assert_rejected(self.token(headers={'jku': 'https://evil.example.test/keys'}))
        self.assert_rejected(jwt.encode({'sub': 'user-a'}, 'untrusted-secret-at-least-32-bytes-long',
                                        algorithm='HS256', headers={'kid': 'key-a', 'typ': 'at+jwt'}))

    def test_unknown_kid_refreshes_pinned_jwks_for_rotation(self):
        self.provider.authenticate(self.token())
        self.keys = [self.jwk(self.private_b, 'key-b')]
        principal = self.provider.authenticate(self.token(private_key=self.private_b,
                                                           kid='key-b'))
        self.assertEqual(principal.subject, 'user-a')
        self.assertEqual(self.fetches, [JWKS_URI, JWKS_URI])
        self.assert_rejected(self.token())

    def test_duplicate_kid_invalid_jwk_and_fetch_failure_never_reuse_stale_keys(self):
        self.provider.authenticate(self.token())
        self.keys = [self.jwk(self.private_a, 'key-a'), self.jwk(self.private_b, 'key-a')]
        self.assert_rejected(self.token(kid='new-key'))
        self.assert_rejected(self.token())  # Failed refresh cannot reuse a prior key.
        self.keys = [self.jwk(self.private_a, 'key-a')]
        provider = self.make_provider(jwks_cache_ttl=timedelta(seconds=1))
        with patch('provisioner.controlplane.authority.oidc.time.monotonic', return_value=100.0):
            provider.authenticate(self.token())
        def failed_fetch(_url):
            raise OSError('offline')
        provider._fetch = failed_fetch
        with patch('provisioner.controlplane.authority.oidc.time.monotonic', return_value=102.0):
            with self.assertRaises(AuthenticationFailed):
                provider.authenticate(self.token())

    def test_configuration_requires_pinned_https_and_bounded_policy(self):
        for changed in ({'jwks_uri': 'http://login.example.test/keys'},
                        {'jwks_uri': 'https://login.example.test/keys#fragment'},
                        {'issuer': 'http://login.example.test/realm'},
                        {'audience': ''}, {'step_up_acr': frozenset()},
                        {'max_token_age': timedelta(days=3)}):
            with self.subTest(changed=changed), self.assertRaises(ValueError):
                self.make_provider(**changed)


if __name__ == '__main__':
    unittest.main()
