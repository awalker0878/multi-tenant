"""Installed service composition refuses missing trust and database roles."""
from __future__ import annotations

import unittest
import json
import tempfile
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from provisioner.controlplane.api.portal import PortalConfig
from provisioner.controlplane.api.server import ServiceSettings, create_postgres_app
from tests.provisioning.evidence.test_runtime import environment as evidence_environment


def settings(**updates):
    values = {
        'runtime_dsn': 'host=db.example.org dbname=hosting user=runtime sslmode=verify-full',
        'authority_dsn': 'host=db.example.org dbname=hosting user=authority sslmode=verify-full',
        'directory_dsn': 'host=db.example.org dbname=hosting user=directory sslmode=verify-full',
        'oidc_issuer': 'https://id.example.org/',
        'oidc_audience': 'hosting-api',
        'oidc_jwks_uri': 'https://id.example.org/keys',
        'step_up_acr': frozenset({'urn:enterprise:step-up'}),
    }
    values.update(updates)
    return ServiceSettings(**values)


class _VerifiedEvidence:
    def require(self, context):
        pass


class ServerCompositionTests(unittest.TestCase):
    def test_installed_settings_require_evidence_and_startup_checks_scopes(self):
        values = evidence_environment() | {
            'HOSTING_AUTHORITY_DSN': settings().authority_dsn,
            'HOSTING_DIRECTORY_DSN': settings().directory_dsn,
            'HOSTING_OIDC_ISSUER': 'https://id.example.org/',
            'HOSTING_OIDC_AUDIENCE': 'hosting-api',
            'HOSTING_OIDC_JWKS_URI': 'https://id.example.org/keys',
            'HOSTING_STEP_UP_ACR': 'urn:enterprise:step-up',
        }
        values['HOSTING_RUNTIME_DSN'] = settings().runtime_dsn
        with self.assertRaises(ValueError):
            ServiceSettings.from_environment(values)
        with tempfile.TemporaryDirectory() as directory:
            scope_file = Path(directory) / 'scopes.json'
            scope_file.write_text(json.dumps([{'organizationId': 'org',
                                               'tenantId': 'tenant'}]))
            values['HOSTING_EVIDENCE_SCOPES_FILE'] = str(scope_file)
            configured = ServiceSettings.from_environment(values)
            seen = []
            gate = type('Gate', (), {'require': lambda _, ctx: seen.append(ctx)})()
            with (patch('provisioner.controlplane.api.server._role_name',
                        side_effect=['runtime', 'authority', 'directory']),
                  patch('provisioner.controlplane.api.server.build_gate',
                        return_value=gate)):
                create_postgres_app(configured)
            self.assertEqual([(ctx.organization_id, ctx.tenant_id) for ctx in seen],
                             [('org', 'tenant')])

    def test_missing_directory_fails_closed(self):
        with self.assertRaises(ValueError):
            ServiceSettings.from_environment({
                'HOSTING_RUNTIME_DSN': settings().runtime_dsn,
                'HOSTING_AUTHORITY_DSN': settings().authority_dsn,
                'HOSTING_OIDC_ISSUER': 'https://id.example.org/',
                'HOSTING_OIDC_AUDIENCE': 'hosting-api',
                'HOSTING_OIDC_JWKS_URI': 'https://id.example.org/keys',
                'HOSTING_STEP_UP_ACR': 'urn:enterprise:step-up',
            })

    def test_database_tls_and_role_separation_required(self):
        with self.assertRaises(ValueError):
            settings(runtime_dsn='host=db.example.org dbname=hosting sslmode=disable')
        with self.assertRaises(ValueError):
            settings(directory_dsn=settings().runtime_dsn)
        with self.assertRaises(ValueError):
            settings(listen_host='0.0.0.0')

    def test_real_repositories_are_composed_only_after_role_probe(self):
        with patch('provisioner.controlplane.api.server._role_name',
                   side_effect=['runtime', 'authority', 'directory']):
            with self.assertRaises(ValueError):
                create_postgres_app(settings())
        with patch('provisioner.controlplane.api.server._role_name',
                   side_effect=['runtime', 'authority', 'directory']) as probe:
            app = create_postgres_app(settings(), evidence_gate=_VerifiedEvidence())
        self.assertEqual(probe.call_count, 3)
        spec = TestClient(app).get('/openapi.json').json()
        self.assertIn('/v1/access/scopes', spec['paths'])
        self.assertIn('/v1/plans/{plan_id}/approvals', spec['paths'])
        self.assertEqual(TestClient(app).get('/v1/access/scopes').status_code, 401)
        self.assertEqual(TestClient(app).get('/portal/').status_code, 404)

    def test_portal_is_only_mounted_with_matching_pinned_oidc_config(self):
        portal = PortalConfig(
            origin='https://control.example.org',
            issuer='https://id.example.org',
            authorize_url='https://id.example.org/authorize',
            token_url='https://id.example.org/token',
            client_id='hosting-public', audience='hosting-api', scope='openid hosting',
            redirect_uri='https://control.example.org/portal/callback',
        )
        with self.assertRaises(ValueError):
            settings(portal=portal)  # OIDC issuer in settings() ends with '/'.
        configured = settings(oidc_issuer='https://id.example.org', portal=portal)
        with patch('provisioner.controlplane.api.server._role_name',
                   side_effect=['runtime', 'authority', 'directory']):
            app = create_postgres_app(configured, evidence_gate=_VerifiedEvidence())
        response = TestClient(app, base_url=portal.origin).get('/portal/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('Content-Security-Policy', response.headers)
        with self.assertRaises(ValueError):
            settings(oidc_issuer='https://id.example.org',
                     portal=PortalConfig(
                         origin=portal.origin, issuer=portal.issuer,
                         authorize_url=portal.authorize_url,
                         token_url=portal.token_url,
                         client_id=portal.client_id, audience=portal.audience,
                         scope=portal.scope, redirect_uri=portal.redirect_uri,
                         step_up_acr='urn:untrusted:acr'))
        allowed = PortalConfig(
            origin=portal.origin, issuer=portal.issuer,
            authorize_url=portal.authorize_url, token_url=portal.token_url,
            client_id=portal.client_id, audience=portal.audience,
            scope=portal.scope, redirect_uri=portal.redirect_uri,
            step_up_acr='urn:enterprise:step-up')
        self.assertEqual(settings(oidc_issuer='https://id.example.org',
                                  portal=allowed).portal.step_up_acr,
                         'urn:enterprise:step-up')

    def test_role_reuse_refuses_startup(self):
        with patch('provisioner.controlplane.api.server._role_name',
                   side_effect=['runtime', 'runtime', 'directory']):
            with self.assertRaises(RuntimeError):
                create_postgres_app(settings(), evidence_gate=_VerifiedEvidence())


if __name__ == '__main__':
    unittest.main()
