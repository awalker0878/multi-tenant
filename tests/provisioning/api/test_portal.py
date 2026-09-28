"""Portal entry, origin and OIDC callback/token boundary tests."""
from __future__ import annotations

import asyncio
import unittest
from unittest.mock import AsyncMock, patch

import httpx
from fastapi import FastAPI
from fastapi.testclient import TestClient

from provisioner.controlplane.api.portal import PortalConfig, mount_portal
from provisioner.controlplane.api.portal import routes

ORIGIN = 'https://mobility.example.org'
ISSUER = 'https://identity.example.org/realms/hosting'
STATE = 's' * 43
VERIFIER = 'v' * 43


def configured(**changes) -> PortalConfig:
    values = dict(origin=ORIGIN, issuer=ISSUER,
                  authorize_url=f'{ISSUER}/protocol/openid-connect/auth',
                  token_url=f'{ISSUER}/protocol/openid-connect/token',
                  client_id='hosting-ui', audience='hosting-api',
                  scope='openid profile hosting.read',
                  redirect_uri=f'{ORIGIN}/portal/callback')
    values.update(changes)
    return PortalConfig(**values)


class PortalTests(unittest.TestCase):
    def setUp(self):
        self.app = FastAPI()
        self.config = configured()
        mount_portal(self.app, self.config)
        self.client = TestClient(self.app, base_url=ORIGIN)

    def test_disabled_without_identity_configuration(self):
        app = FastAPI()
        mount_portal(app, None)
        client = TestClient(app, base_url=ORIGIN)
        for path in ('/portal/', '/portal/config.json', '/portal/token'):
            self.assertEqual(client.get(path).status_code, 404)

    def test_configuration_requires_exact_https_origin_and_issuer_endpoints(self):
        cases = (
            {'origin': 'http://mobility.example.org'},
            {'origin': 'https://mobility.example.org:443'},
            {'redirect_uri': 'https://other.example.org/portal/callback'},
            {'redirect_uri': f'{ORIGIN}/portal/callback?next=other'},
            {'token_url': 'https://attacker.example.org/token'},
            {'authorize_url': 'http://identity.example.org/auth'},
            {'scope': 'profile offline_access'},
            {'scope': 'openid offline_access'},
            {'audience': ''},
            {'step_up_acr': ''},
            {'step_up_acr': 'urn:bad acr'},
        )
        for change in cases:
            with self.subTest(change=change), self.assertRaises(ValueError):
                configured(**change)

    def test_self_hosted_assets_and_origin_policy(self):
        page = self.client.get('/portal/')
        self.assertEqual(page.status_code, 200)
        self.assertIn('src="app.js"', page.text)
        self.assertIn('href="style.css"', page.text)
        self.assertEqual(page.headers['cache-control'], 'no-store')
        self.assertIn("default-src 'none'", page.headers['content-security-policy'])
        self.assertIn("frame-ancestors 'none'", page.headers['content-security-policy'])
        self.assertEqual(page.headers['cross-origin-opener-policy'], 'same-origin-allow-popups')
        js = self.client.get('/portal/app.js')
        self.assertEqual(js.status_code, 200)
        self.assertIn("/v1/access/scopes", js.text)
        self.assertIn("response_mode', 'form_post'", js.text)
        self.assertIn("code_challenge_method', 'S256'", js.text)
        self.assertNotIn('localStorage', js.text)
        self.assertNotIn('sessionStorage', js.text)
        settings = self.client.get('/portal/config.json').json()
        self.assertEqual(settings['origin'], ORIGIN)
        self.assertNotIn('tokenUrl', settings)
        self.assertNotIn('secret', settings)
        self.assertIsNone(settings['stepUpAcr'])
        self.assertEqual(TestClient(self.app, base_url='https://other.example.org').get('/portal/').status_code, 421)
        self.assertEqual(TestClient(self.app, base_url='http://mobility.example.org').get('/portal/').status_code, 421)
        # Only the trusted ingress may rewrite the ASGI scheme. A forwarded
        # header passed straight to the app has no authority by itself.
        self.assertEqual(TestClient(self.app, base_url='http://mobility.example.org').get(
            '/portal/', headers={'X-Forwarded-Proto': 'https'}).status_code, 421)

    def test_configured_step_up_acr_is_exposed_without_any_secret(self):
        app = FastAPI()
        mount_portal(app, configured(step_up_acr='urn:enterprise:mfa'))
        settings = TestClient(app, base_url=ORIGIN).get('/portal/config.json').json()
        self.assertEqual(settings['stepUpAcr'], 'urn:enterprise:mfa')
        self.assertNotIn('tokenUrl', settings)

    def test_form_post_callback_never_accepts_query_code_or_wrong_issuer(self):
        self.assertEqual(self.client.get(f'/portal/callback?code=secret&state={STATE}').status_code, 405)
        self.assertEqual(self.client.post('/portal/callback', data={'code': 'abc12345', 'state': STATE,
                                                                  'iss': 'https://other.example.org'}).status_code, 400)
        self.assertEqual(self.client.post('/portal/callback', data={'code': 'abc12345',
                                                                  'state': 'short'}).status_code, 400)
        duplicate = f'code=first&code=second&state={STATE}'.encode()
        self.assertEqual(self.client.post('/portal/callback', content=duplicate,
                                          headers={'Content-Type': 'application/x-www-form-urlencoded'}).status_code, 400)
        oversized = b'code=' + b'a' * 8192
        self.assertEqual(self.client.post('/portal/callback', content=oversized,
                                          headers={'Content-Type': 'application/x-www-form-urlencoded'}).status_code, 413)

    def test_callback_escapes_untrusted_code_and_targets_exact_origin(self):
        code = 'abc12345</script><script>alert(1)</script>'
        response = self.client.post('/portal/callback', data={'code': code, 'state': STATE,
                                                              'iss': ISSUER})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertNotIn(code, response.text)
        self.assertIn('\\u003c/script\\u003e', response.text)
        self.assertIn('"https://mobility.example.org"', response.text)
        self.assertIn("script-src 'nonce-", response.headers['content-security-policy'])
        self.assertEqual(response.headers['cache-control'], 'no-store')

    def test_token_proxy_requires_same_origin_and_valid_pkce_request(self):
        payload = {'code': 'code12345', 'verifier': VERIFIER}
        with patch.object(routes, '_exchange_code', new_callable=AsyncMock) as exchange:
            exchange.return_value = {'access_token': 'opaque-access', 'token_type': 'Bearer',
                                     'expires_in': 300}
            for origin in (None, 'https://other.example.org'):
                headers = {} if origin is None else {'Origin': origin}
                response = self.client.post('/portal/token', json=payload, headers=headers)
                self.assertEqual(response.status_code, 403)
            for bad in ({'code': 'short', 'verifier': VERIFIER},
                        {'code': 'code12345', 'verifier': 'short'},
                        {'code': 'code12345', 'verifier': VERIFIER, 'token_url': 'https://evil.example'}):
                response = self.client.post('/portal/token', json=bad, headers={'Origin': ORIGIN})
                self.assertEqual(response.status_code, 400)
            self.assertEqual(exchange.await_count, 0)
            response = self.client.post('/portal/token', json=payload, headers={'Origin': ORIGIN})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()['access_token'], 'opaque-access')
            self.assertEqual(response.headers['cache-control'], 'no-store')
            exchange.assert_awaited_once_with(self.config, 'code12345', VERIFIER)

    def test_token_exchange_only_returns_bearer_access_token(self):
        requests = []
        def handler(request: httpx.Request) -> httpx.Response:
            requests.append(request)
            return httpx.Response(200, json={'access_token': 'opaque-access',
                                              'token_type': 'Bearer', 'expires_in': 600,
                                              'refresh_token': 'must-not-return',
                                              'id_token': 'must-not-return'})
        real_client = httpx.AsyncClient
        transport = httpx.MockTransport(handler)
        def factory(**kwargs):
            return real_client(transport=transport, **kwargs)
        with patch.object(routes.httpx, 'AsyncClient', side_effect=factory):
            result = asyncio.run(routes._exchange_code(self.config, 'code12345', VERIFIER))
        self.assertEqual(result, {'access_token': 'opaque-access', 'token_type': 'Bearer',
                                  'expires_in': 600})
        self.assertEqual(len(requests), 1)
        self.assertEqual(str(requests[0].url), self.config.token_url)
        self.assertEqual(requests[0].method, 'POST')
        self.assertIn(b'code_verifier=' + VERIFIER.encode(), requests[0].content)
        self.assertNotIn(b'client_secret', requests[0].content)


if __name__ == '__main__':
    unittest.main()
