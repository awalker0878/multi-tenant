"""Fail-closed portal assets and OIDC public-client token exchange.

The browser holds the PKCE verifier, OAuth state and access token only in the
active page's JavaScript memory. Authorization responses use form_post so no
code or bearer token enters a URL. The fixed token proxy avoids relying on an
identity provider's browser CORS policy. The control API verifies the bearer
credential on every data request; this module grants no roles itself.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from importlib.resources import files
from secrets import token_urlsafe
from urllib.parse import parse_qs, urlsplit

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse, Response

_MAX_BODY = 8192
_STATE = re.compile(r'^[A-Za-z0-9_-]{43,128}$')
_VERIFIER = re.compile(r'^[A-Za-z0-9._~-]{43,128}$')


def _https_url(value: str) -> tuple[str, str]:
    if not isinstance(value, str) or len(value) > 2048:
        raise ValueError('Portal URLs must be HTTPS strings')
    parsed = urlsplit(value)
    if (parsed.scheme != 'https' or not parsed.hostname or parsed.username
            or parsed.password or parsed.query or parsed.fragment
            or parsed.netloc != parsed.netloc.lower() or '\\' in value):
        raise ValueError('Portal URLs must be canonical HTTPS URLs without credentials, query or fragment')
    try:
        _ = parsed.port
    except ValueError as exc:
        raise ValueError('Invalid HTTPS port') from exc
    return f'https://{parsed.netloc}', parsed.path


@dataclass(frozen=True)
class PortalConfig:
    origin: str
    issuer: str
    authorize_url: str
    token_url: str
    client_id: str
    audience: str
    scope: str
    redirect_uri: str
    step_up_acr: str | None = None

    def __post_init__(self) -> None:
        origin, path = _https_url(self.origin)
        if self.origin != origin or path or urlsplit(self.origin).port == 443:
            raise ValueError('Portal origin must be an exact HTTPS origin')
        issuer_origin, _ = _https_url(self.issuer)
        if self.issuer.endswith('/'):
            raise ValueError('Issuer URL must not have a trailing slash')
        for endpoint in (self.authorize_url, self.token_url):
            endpoint_origin, endpoint_path = _https_url(endpoint)
            if endpoint_origin != issuer_origin or not endpoint_path.startswith('/'):
                raise ValueError('OIDC endpoints must be on the configured issuer origin')
        if self.redirect_uri != f'{origin}/portal/callback':
            raise ValueError('Redirect URI must exactly match the portal callback')
        if (not isinstance(self.client_id, str) or not self.client_id
                or len(self.client_id) > 256 or any(ord(c) < 33 for c in self.client_id)):
            raise ValueError('A public OIDC client ID is required')
        if (not isinstance(self.audience, str) or not self.audience
                or len(self.audience) > 512 or any(ord(c) < 33 for c in self.audience)):
            raise ValueError('A control-API audience is required')
        if (not isinstance(self.scope, str) or 'openid' not in self.scope.split()
                or 'offline_access' in self.scope.split()
                or len(self.scope) > 512 or any(ord(c) < 32 for c in self.scope)):
            raise ValueError('OIDC scope must contain openid and exclude offline_access')
        if self.step_up_acr is not None and (
                not isinstance(self.step_up_acr, str) or not self.step_up_acr
                or len(self.step_up_acr) > 256
                or any(c.isspace() or ord(c) < 33 for c in self.step_up_acr)):
            raise ValueError('Step-up ACR must be one configured assurance value')


def _headers(csp: str) -> dict[str, str]:
    return {
        'Cache-Control': 'no-store',
        'Content-Security-Policy': csp,
        'Cross-Origin-Opener-Policy': 'same-origin-allow-popups',
        'Referrer-Policy': 'no-referrer',
        'X-Content-Type-Options': 'nosniff',
        'X-Frame-Options': 'DENY',
        'Permissions-Policy': 'camera=(), microphone=(), geolocation=()',
    }


_ASSET_CSP = ("default-src 'none'; base-uri 'none'; frame-ancestors 'none'; "
              "object-src 'none'; script-src 'self'; style-src 'self'; "
              "connect-src 'self'; form-action 'none'")


def _asset(name: str) -> str:
    return files(__package__).joinpath(name).read_text(encoding='utf-8')


def _same_origin(request: Request, origin: str) -> bool:
    # A trusted TLS ingress must preserve the external Host and HTTPS scheme.
    return f'{request.url.scheme}://{request.url.netloc}' == origin


async def _limited_body(request: Request) -> bytes | None:
    body = bytearray()
    async for chunk in request.stream():
        body.extend(chunk)
        if len(body) > _MAX_BODY:
            return None
    return bytes(body)


def _safe_script_json(value: dict) -> str:
    # JSON in a script element must not contain an attacker-controlled closing tag.
    return json.dumps(value, separators=(',', ':')).replace('<', '\\u003c').replace('>', '\\u003e').replace('&', '\\u0026')


async def _exchange_code(config: PortalConfig, code: str, verifier: str) -> dict | None:
    try:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=False,
                                     trust_env=False) as client:
            response = await client.post(config.token_url, data={
                'grant_type': 'authorization_code',
                'client_id': config.client_id,
                'redirect_uri': config.redirect_uri,
                'code': code,
                'code_verifier': verifier,
            }, headers={'Accept': 'application/json'})
        if response.status_code != 200 or len(response.content) > 16384:
            return None
        payload = response.json()
    except (httpx.HTTPError, ValueError):
        return None
    if not isinstance(payload, dict):
        return None
    token = payload.get('access_token')
    token_type = payload.get('token_type')
    if (not isinstance(token, str) or not token or len(token) > 16384
            or any(ord(c) < 33 for c in token)
            or not isinstance(token_type, str) or token_type.lower() != 'bearer'):
        return None
    result = {'access_token': token, 'token_type': 'Bearer'}
    lifetime = payload.get('expires_in')
    if type(lifetime) is int and 0 < lifetime <= 86400:
        result['expires_in'] = lifetime
    return result


def mount_portal(app: FastAPI, config: PortalConfig | None) -> None:
    """Mount only when fully configured; no development/default identity path."""
    if config is None:
        return
    if not isinstance(config, PortalConfig):
        raise TypeError('portal config must be a validated PortalConfig')

    def wrong_origin(request: Request) -> Response | None:
        if not _same_origin(request, config.origin):
            return PlainTextResponse('Unknown portal origin', status_code=421,
                                     headers=_headers(_ASSET_CSP))
        return None

    @app.get('/portal/', include_in_schema=False)
    def index(request: Request) -> Response:
        if rejected := wrong_origin(request):
            return rejected
        return HTMLResponse(_asset('index.html'), headers=_headers(_ASSET_CSP))

    @app.get('/portal/app.js', include_in_schema=False)
    def javascript(request: Request) -> Response:
        if rejected := wrong_origin(request):
            return rejected
        return Response(_asset('app.js'), media_type='text/javascript; charset=utf-8',
                        headers=_headers(_ASSET_CSP))

    @app.get('/portal/application_drafts.js', include_in_schema=False)
    def application_draft_javascript(request: Request) -> Response:
        if rejected := wrong_origin(request):
            return rejected
        return Response(_asset('application_drafts.js'), media_type='text/javascript; charset=utf-8',
                        headers=_headers(_ASSET_CSP))

    @app.get('/portal/style.css', include_in_schema=False)
    def stylesheet(request: Request) -> Response:
        if rejected := wrong_origin(request):
            return rejected
        return Response(_asset('style.css'), media_type='text/css; charset=utf-8',
                        headers=_headers(_ASSET_CSP))

    @app.get('/portal/config.json', include_in_schema=False)
    def browser_config(request: Request) -> Response:
        if rejected := wrong_origin(request):
            return rejected
        return JSONResponse({
            'origin': config.origin,
            'issuer': config.issuer,
            'authorizeUrl': config.authorize_url,
            'clientId': config.client_id,
            'audience': config.audience,
            'scope': config.scope,
            'redirectUri': config.redirect_uri,
            'stepUpAcr': config.step_up_acr,
        }, headers=_headers(_ASSET_CSP))

    @app.post('/portal/callback', include_in_schema=False)
    async def callback(request: Request) -> Response:
        if rejected := wrong_origin(request):
            return rejected
        if request.headers.get('content-type', '').split(';', 1)[0].strip().lower() != 'application/x-www-form-urlencoded':
            return PlainTextResponse('Invalid callback', status_code=400,
                                     headers=_headers(_ASSET_CSP))
        body = await _limited_body(request)
        if body is None:
            return PlainTextResponse('Invalid callback', status_code=413,
                                     headers=_headers(_ASSET_CSP))
        try:
            fields = parse_qs(body.decode('utf-8'), keep_blank_values=True,
                              strict_parsing=True)
        except (UnicodeDecodeError, ValueError):
            fields = {}
        if any(len(values) != 1 for values in fields.values()):
            fields = {}
        state = fields.get('state', [''])[0]
        code = fields.get('code', [''])[0]
        error = fields.get('error', [''])[0]
        issuer = fields.get('iss', [config.issuer])[0]
        if (not _STATE.fullmatch(state) or issuer != config.issuer
                or (bool(code) == bool(error)) or len(code) > 4096
                or len(error) > 256
                or any(ord(c) < 32 for c in code + error)):
            return PlainTextResponse('Invalid callback', status_code=400,
                                     headers=_headers(_ASSET_CSP))
        payload = {'kind': 'mobility-oidc-response', 'state': state,
                   'code': code if code else None,
                   'error': error if error else None,
                   'issuer': issuer}
        nonce = token_urlsafe(24)
        script = (f'<script nonce="{nonce}">'
                  f'window.opener?.postMessage({_safe_script_json(payload)},'
                  f'{_safe_script_json(config.origin)});window.close();'
                  '</script>')
        html = ('<!doctype html><html lang="en"><meta charset="utf-8">'
                '<title>Return to workload mobility</title>'
                '<body><p>Return to the workload mobility portal.</p>'
                + script + '</body></html>')
        csp = ("default-src 'none'; base-uri 'none'; frame-ancestors 'none'; "
               "object-src 'none'; form-action 'none'; "
               f"script-src 'nonce-{nonce}'")
        return HTMLResponse(html, headers=_headers(csp))

    @app.post('/portal/token', include_in_schema=False)
    async def token(request: Request) -> Response:
        if rejected := wrong_origin(request):
            return rejected
        if request.headers.get('origin') != config.origin:
            return JSONResponse({'error': 'origin_required'}, status_code=403,
                                headers=_headers(_ASSET_CSP))
        if request.headers.get('content-type', '').split(';', 1)[0].strip().lower() != 'application/json':
            return JSONResponse({'error': 'request_invalid'}, status_code=400,
                                headers=_headers(_ASSET_CSP))
        body = await _limited_body(request)
        if body is None:
            return JSONResponse({'error': 'request_invalid'}, status_code=413,
                                headers=_headers(_ASSET_CSP))
        try:
            payload = json.loads(body)
        except (UnicodeDecodeError, ValueError):
            payload = None
        if (not isinstance(payload, dict) or set(payload) != {'code', 'verifier'}
                or not isinstance(payload.get('code'), str)
                or not 8 <= len(payload['code']) <= 4096
                or any(ord(c) < 32 for c in payload['code'])
                or not isinstance(payload.get('verifier'), str)
                or not _VERIFIER.fullmatch(payload['verifier'])):
            return JSONResponse({'error': 'request_invalid'}, status_code=400,
                                headers=_headers(_ASSET_CSP))
        result = await _exchange_code(config, payload['code'], payload['verifier'])
        if result is None:
            return JSONResponse({'error': 'exchange_failed'}, status_code=502,
                                headers=_headers(_ASSET_CSP))
        return JSONResponse(result, headers=_headers(_ASSET_CSP))
