"""Worker-only mTLS listener for exact, read-only credential handoff.

Mutations remain held: no native adapter has been qualified to turn a B11
intent into a platform call. A trusted workflow must register the B11 lease
and issue the B10 grant before a worker can request even a read credential.
"""
from __future__ import annotations

import ipaddress
import json
import socket
import ssl
import threading
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Callable

from provisioner.controlplane.authority.model import PlanScope
from provisioner.controlplane.persistence import TenantContext
from provisioner.controlplane.reconciliation.registry import NativeLeaseAuthority

from .grants import CredentialBroker, GrantDenied, PostgresWorkerGrants, _ID
from .pki import MutualTlsWorkerVerifier
from .vault import VaultDynamicCredentialIssuer, VaultWrappedCredential

_SCOPE_KEYS = frozenset({'organizationId', 'tenantId', 'locationId',
                         'securityDomainId', 'endpointId', 'nativeScopeId',
                         'platformFamily'})
_REQUEST_KEYS = frozenset({'grantId', 'jobId', 'stepId', 'operationId',
                           'operationKind', 'scope', 'leaseKey', 'leaseEpoch'})
_MAX_BODY = 8192


class _BadRequest(ValueError):
    pass


def _unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise _BadRequest('Duplicate JSON fields are forbidden')
        result[key] = value
    return result


def _not_constant(value):
    raise _BadRequest('Nonfinite JSON number is forbidden')


class SiteWorkerServer(ThreadingHTTPServer):
    """Bind only to a site management address; transport identity is mandatory."""

    daemon_threads = True
    allow_reuse_address = False
    request_queue_size = 16

    def __init__(self, address: tuple[str, int], *, site_id: str,
                 allowed_read_scopes: frozenset[PlanScope],
                 verifier: MutualTlsWorkerVerifier,
                 grants: PostgresWorkerGrants,
                 issuer: VaultDynamicCredentialIssuer):
        try:
            bind_ip = ipaddress.ip_address(address[0])
        except (ValueError, TypeError, IndexError) as exc:
            raise ValueError('Bind the worker listener to a specific management IP') from exc
        if (not isinstance(site_id, str) or not _ID.fullmatch(site_id)
                or bind_ip.is_unspecified or len(address) != 2
                or type(address[1]) is not int or not 0 <= address[1] <= 65535
                or not isinstance(allowed_read_scopes, frozenset)
                or not allowed_read_scopes
                or any(not isinstance(scope, PlanScope) or scope.site_id != site_id
                       for scope in allowed_read_scopes)
                or not isinstance(verifier, MutualTlsWorkerVerifier)
                or not callable(getattr(grants, 'with_authorized_reference', None))
                or not callable(getattr(issuer, 'issue', None))):
            raise ValueError('A pinned TLS site, exact routes, grants and Vault issuer are required')
        self.site_id = site_id
        self.address_family = socket.AF_INET6 if bind_ip.version == 6 else socket.AF_INET
        self.allowed_read_scopes = allowed_read_scopes
        self.verifier = verifier
        self.broker = CredentialBroker(verifier, grants, issuer)
        self._slots = threading.BoundedSemaphore(32)
        super().__init__(address, _WorkerHandler)

    def get_request(self):
        raw, address = super().get_request()
        raw.settimeout(10)
        return raw, address

    def process_request(self, request, client_address):
        if not self._slots.acquire(blocking=False):
            request.close()
            return
        try:
            super().process_request(request, client_address)
        except Exception:
            self._slots.release()
            raise

    def process_request_thread(self, request, client_address):
        # TLS handshakes run under a bounded worker slot, never on the accept
        # loop. A stalled or unauthenticated peer cannot serialize the site.
        try:
            with self.verifier.context.wrap_socket(request, server_side=True) as peer:
                super().process_request_thread(peer, client_address)
        except (ssl.SSLError, TimeoutError, OSError):
            request.close()
        finally:
            self._slots.release()


def create_site_worker_server(address: tuple[str, int], *, site_id: str,
                              allowed_read_scopes: frozenset[PlanScope],
                              verifier: MutualTlsWorkerVerifier,
                              connect: Callable,
                              issuer: VaultDynamicCredentialIssuer) -> SiteWorkerServer:
    """Wire the real PostgreSQL grant and B11 owner lease authorities."""
    if not callable(connect) or not isinstance(issuer, VaultDynamicCredentialIssuer):
        raise ValueError('A PostgreSQL connection and real Vault issuer are required')
    leases = NativeLeaseAuthority(connect)
    grants = PostgresWorkerGrants(connect, leases)
    return SiteWorkerServer(address, site_id=site_id,
                            allowed_read_scopes=allowed_read_scopes,
                            verifier=verifier, grants=grants, issuer=issuer)


class _WorkerHandler(BaseHTTPRequestHandler):
    server: SiteWorkerServer

    def log_message(self, *_args):
        # The request and response can include an opaque bearer handle.
        pass

    def _reply(self, status: int, body: dict):
        encoded = json.dumps(body, separators=(',', ':')).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Pragma', 'no-cache')
        self.send_header('Content-Length', str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def do_POST(self):
        if self.path != '/v1/worker/credentials':
            self._reply(404, {'error': 'UNKNOWN_ROUTE'})
            return
        try:
            # No proxy or application-level identity may replace this socket.
            identity = self.server.verifier.verify(self.connection)
            if any(header in self.headers for header in (
                    'Forwarded', 'X-Forwarded-For', 'X-Forwarded-Client-Cert',
                    'X-Client-Cert', 'X-SSL-Client-Cert')):
                raise _BadRequest('Forwarded identities are forbidden')
            lengths = self.headers.get_all('Content-Length', [])
            if (len(lengths) != 1 or not lengths[0].isdigit()
                    or not 0 < int(lengths[0]) <= _MAX_BODY
                    or self.headers.get('Transfer-Encoding') is not None
                    or self.headers.get('Content-Encoding') is not None
                    or self.headers.get('Content-Type') != 'application/json'):
                raise _BadRequest('An exact bounded JSON request is required')
            request = json.loads(self.rfile.read(int(lengths[0])),
                                 object_pairs_hook=_unique_pairs,
                                 parse_constant=_not_constant)
            if not isinstance(request, dict) or request.keys() != _REQUEST_KEYS:
                raise _BadRequest('Exact credential request fields are required')
            if request['operationKind'] != 'DISCOVER_READ':
                self._reply(423, {'error': 'NATIVE_ROUTE_NOT_QUALIFIED'})
                return
            if (not isinstance(request['scope'], dict)
                    or request['scope'].keys() != _SCOPE_KEYS):
                raise _BadRequest('Exact native scope is required')
            scope = PlanScope.from_record(request['scope'])
            if (scope not in self.server.allowed_read_scopes
                    or (scope.organization_id, scope.tenant_id, scope.site_id) !=
                    (identity.organization_id, identity.tenant_id, identity.site_id)):
                raise GrantDenied('Worker site, tenant or route is not admitted')
            if (any(not isinstance(request[key], str) or not _ID.fullmatch(request[key])
                    for key in ('grantId', 'jobId', 'stepId', 'operationId', 'leaseKey'))
                    or type(request['leaseEpoch']) is not int
                    or request['leaseEpoch'] < 1):
                raise _BadRequest('Exact grant and lease identifiers are required')
            context = TenantContext(identity.organization_id, identity.tenant_id)
            handle = self.server.broker.acquire(
                self.connection, context, request['grantId'], job_id=request['jobId'],
                step_id=request['stepId'], operation_id=request['operationId'],
                operation_kind='DISCOVER_READ', operation_scope=scope,
                lease_key=request['leaseKey'], lease_epoch=request['leaseEpoch'])
            if not isinstance(handle, VaultWrappedCredential):
                raise GrantDenied('A one-use Vault response-wrapped credential is required')
            if (handle.grant_id != request['grantId']
                    or handle.expires_at <= datetime.now(timezone.utc)):
                raise GrantDenied('Vault response is no longer bound to the current grant')
            self._reply(200, {
                'wrappingToken': handle.wrapping_token,
                'creationPath': handle.creation_path,
                'expiresAt': handle.expires_at.astimezone(timezone.utc).isoformat(),
                'grantId': handle.grant_id,
            })
        except (ValueError, KeyError, TypeError, json.JSONDecodeError, _BadRequest):
            self._reply(400, {'error': 'INVALID_REQUEST'})
        except GrantDenied:
            self._reply(403, {'error': 'WORKER_AUTHORITY_DENIED'})
        except Exception:
            # The denied error is deliberately generic: no SQL, role reference,
            # Vault token or native scope detail is returned to the worker.
            self._reply(503, {'error': 'WORKER_SERVICE_UNAVAILABLE'})

    def do_GET(self):
        self._reply(405, {'error': 'METHOD_NOT_ALLOWED'})
