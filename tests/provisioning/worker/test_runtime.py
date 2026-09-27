"""Installed worker startup rejects broad database roles and vague routes."""
from __future__ import annotations

import json
import unittest
from dataclasses import replace

from provisioner.controlplane.worker.runtime import (
    SiteWorkerSettings, _require_read_only_role)


class Result:
    def __init__(self, value):
        self.value = value

    def fetchone(self):
        return self.value


class RoleConnection:
    autocommit = False

    def __init__(self, rows):
        self.rows = iter(rows)

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        pass

    def execute(self, _statement, _parameters=None):
        return Result(next(self.rows))


class SiteWorkerRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.scope = {
            'organizationId': 'org-01', 'tenantId': 'tenant-01',
            'locationId': 'site-01', 'securityDomainId': 'sd-01',
            'endpointId': 'endpoint-01', 'nativeScopeId': 'native-01',
            'platformFamily': 'vmware',
        }
        self.route = {'scope': self.scope, 'reference': 'vault:site-read',
                      'apiPath': 'platform/creds/site-read',
                      'maxCredentialTtlSeconds': 120}
        self.env = {
            'HOSTING_SITE_POSTGRES_DSN':
                'postgresql://hosting_site_worker@db.example/hosting?sslmode=verify-full&connect_timeout=5&sslrootcert=/etc/worker/db-ca.pem',
            'HOSTING_SITE_POSTGRES_ROLE': 'hosting_site_worker',
            'HOSTING_SITE_ID': 'site-01', 'HOSTING_SITE_BIND_IP': '127.0.0.1',
            'HOSTING_SITE_BIND_PORT': '8443',
            'HOSTING_SITE_TLS_CERT': '/etc/worker/server.pem',
            'HOSTING_SITE_TLS_KEY': '/etc/worker/server.key',
            'HOSTING_SITE_TLS_CA': '/etc/worker/ca.pem',
            'HOSTING_SITE_TLS_CRL': '/etc/worker/crl.pem',
            'HOSTING_SITE_TRUST_DOMAIN': 'workers.example',
            'HOSTING_SITE_VAULT_URL': 'https://vault.example:8200',
            'HOSTING_SITE_VAULT_CA': '/etc/worker/vault-ca.pem',
            'HOSTING_SITE_VAULT_TOKEN_FILE': '/run/vault/token',
            'HOSTING_SITE_READ_ROUTES_JSON': json.dumps([self.route]),
        }

    def test_exact_read_route_and_dedicated_role(self):
        settings = SiteWorkerSettings.from_environment(self.env)
        self.assertEqual(settings.roles[0].scope.site_id, 'site-01')
        self.assertEqual(settings.roles[0].operation_kind, 'DISCOVER_READ')
        self.assertEqual(settings.roles[0].max_credential_ttl.total_seconds(), 120)
        rows = [('hosting_site_worker', 'hosting_site_worker', False, False, True),
                (False, False, False, False, False), (False,),
                (False, False, False), (True,), (False, False), (False,),
                (True,), (True, True, True, True)]
        _require_read_only_role(lambda: RoleConnection(rows), settings)

    def test_privileged_and_incomplete_role_are_rejected(self):
        settings = SiteWorkerSettings.from_environment(self.env)
        good = [('hosting_site_worker', 'hosting_site_worker', False, False, True),
                (False, False, False, False, False), (False,),
                (False, False, False), (True,), (False, False), (False,),
                (True,), (True, True, True, True)]
        for index, value in ((0, ('hosting_site_worker', 'hosting_site_worker',
                                  True, False, True)),
                             (1, (True, False, False, False, False)),
                             (2, (True,)), (3, (False, False, True)),
                             (4, (False,)), (5, (True, False)),
                             (6, (True,)), (7, (False,)),
                             (8, (True, True, False, True))):
            rows = list(good)
            rows[index] = value
            with self.subTest(index=index), self.assertRaises(RuntimeError):
                _require_read_only_role(lambda rows=rows: RoleConnection(rows),
                                        settings)

    def test_unqualified_or_ambiguous_route_rejected_before_listen(self):
        settings = SiteWorkerSettings.from_environment(self.env)
        with self.assertRaises(ValueError):
            replace(settings, postgres_dsn=settings.postgres_dsn.replace(
                'verify-full', 'disable'))
        with self.assertRaises(ValueError):
            replace(settings, postgres_role='other_role')
        with self.assertRaises(ValueError):
            replace(settings, site_id='another-site')
        with self.assertRaises(ValueError):
            replace(settings, roles=settings.roles + settings.roles)
        wrong_tenant_role = replace(settings.roles[0], scope=replace(
            settings.roles[0].scope, tenant_id='other-tenant'))
        with self.assertRaises(ValueError):
            replace(settings, roles=settings.roles + (wrong_tenant_role,))
        for raw in (
            '[{"scope": {}, "scope": {}}]',
            json.dumps([dict(self.route, maxCredentialTtlSeconds=True)]),
            json.dumps([dict(self.route, operationKind='VM_POWER')]),
            json.dumps([dict(self.route, scope=dict(self.scope, locationId='other-site'))]),
        ):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                SiteWorkerSettings.from_environment(dict(
                    self.env, HOSTING_SITE_READ_ROUTES_JSON=raw))

if __name__ == '__main__':
    unittest.main()
