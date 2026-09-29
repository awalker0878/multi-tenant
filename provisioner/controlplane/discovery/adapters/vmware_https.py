"""Actual bounded HTTPS reads for the selected vCenter discovery collector.

This is not a mutation client or an authentication fallback. The native owner
supplies an independently signed, exact-campaign session binding. The existing
signed campaign and independent read-only witness are checked around every read.
Only folder-filtered VM lists and detail IDs returned by those lists are sent.
"""
from __future__ import annotations

import hashlib
import http.client
import re
import socket
import ssl
import time
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock, Timer
from typing import Callable
from urllib.parse import urlencode, urlsplit

from .vmware_rest import (API_RELEASE, PROFILE, FolderSelection, RestResponse,
                          collect_vmware_vms)
from ..model import DiscoveryCampaignAuthorization, _id, _utc
from ..native_credentials import (NativeReadHeld, SignedFileVmwareCredentialSource,
                                  decode_json, read_protected)
from ..trust import BoundDiscoveryIngestVerifier


class VmwareHttpsTransport:
    """One serial, budgeted campaign over a pinned IP and verified TLS hostname.

    No DNS discovery, proxies, redirects, cookies, login or automatic retry is
    used. The separately signed credential binds URL, IP, CA, API, folders and
    token bytes. A deadline shuts down stalled sockets, including slow headers.
    Native session issuance, witness production and installed qualification are
    external responsibilities, not synthesized from these successful reads.
    """
    def __init__(self, campaign: DiscoveryCampaignAuthorization, selection: FolderSelection,
                 environment_id: str, *, verifier: BoundDiscoveryIngestVerifier,
                 credentials: SignedFileVmwareCredentialSource, ca_bundle: str | Path,
                 timeout: float = 5.0, max_response_bytes: int = 4 * 1024 * 1024,
                 clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc)):
        if (not isinstance(campaign, DiscoveryCampaignAuthorization)
                or not isinstance(selection, FolderSelection) or campaign.scope != selection.scope
                or campaign.scope.platform_family != 'vmware' or campaign.collector_id != PROFILE
                or selection.api_release != API_RELEASE or not _id(environment_id)
                or not isinstance(selection.coverage_digest, str)
                or not re.fullmatch(r'[0-9a-f]{64}', selection.coverage_digest)
                or not isinstance(selection.folder_ids, tuple) or not 1 <= len(selection.folder_ids) <= 128
                or len(set(selection.folder_ids)) != len(selection.folder_ids)
                or any(not isinstance(f, str) or not re.fullmatch(r'group-v[1-9][0-9]{0,15}', f)
                       for f in selection.folder_ids)
                or not re.fullmatch(r'datacenter-[1-9][0-9]{0,15}', campaign.scope.native_scope_id)
                or not isinstance(verifier, BoundDiscoveryIngestVerifier)
                or not isinstance(credentials, SignedFileVmwareCredentialSource)
                or type(timeout) not in (float, int) or not 0 < timeout <= 15
                or type(max_response_bytes) is not int or not 1024 <= max_response_bytes <= 4 * 1024 * 1024
                or not callable(clock)):
            raise ValueError('Exact VMware campaign and bounded native read configuration required')
        self._campaign, self._selection, self._environment = campaign, selection, environment_id
        self._verifier, self._credentials, self._ca = verifier, credentials, Path(ca_bundle)
        self._timeout, self._max_bytes, self._clock = timeout, max_response_bytes, clock
        self._last_time = campaign.issued_at
        self._lock = Lock()
        self._seen_vms: set[str] = set()
        self._requests = 0
        self._request_limit = min(50000, campaign.max_objects) + len(selection.folder_ids)
        self._list_paths = {'/api/vcenter/vm?' + urlencode((('folders', folder),
            ('datacenters', campaign.scope.native_scope_id))) for folder in selection.folder_ids}

    @property
    def scope(self):
        return self._campaign.scope

    @property
    def api_release(self):
        return API_RELEASE

    @property
    def read_only(self):
        return True  # The GET allowlist is enforced here; native RBAC is witnessed below.

    def _now(self):
        now = self._clock()
        if not _utc(now) or not self._last_time <= now < self._campaign.expires_at:
            raise NativeReadHeld('Native read campaign expired or clock regressed')
        self._last_time = now
        return now

    def _authorize(self):
        now = self._now()
        material = self._credentials.read(self._campaign, self._selection,
                                          self._environment, checked_at=now)
        self._verifier.verify_read_credential(self._campaign, self._environment, now,
            material.credential_reference, self._credentials.authority_public_key)
        # Verification may itself take time; never carry an expired check to I/O.
        self._now()
        return material

    def collect(self):
        pages = collect_vmware_vms(self._campaign, self._selection, self, clock=self._now)
        self._authorize()
        return pages

    def get(self, path: str) -> RestResponse:
        if not self._lock.acquire(timeout=self._timeout):
            raise NativeReadHeld('Native discovery read is already active')
        try:
            if (not isinstance(path, str) or path not in self._list_paths
                    and not (path.startswith('/api/vcenter/vm/')
                             and path.removeprefix('/api/vcenter/vm/') in self._seen_vms)
                    or self._requests >= self._request_limit):
                raise NativeReadHeld('Native read path or request budget is not admitted')
            self._requests += 1
            return self._get(path)
        except Exception:
            # Neither provider exceptions nor native error bodies enter evidence.
            raise NativeReadHeld('Verified VMware HTTPS read unavailable') from None
        finally:
            self._lock.release()

    def _get(self, path: str) -> RestResponse:
        material = self._authorize()
        ca = read_protected(self._ca, 1024 * 1024, secret=False)
        if hashlib.sha256(ca).hexdigest() != material.ca_digest:
            raise NativeReadHeld('Native trust bundle differs from the signed binding')
        context = ssl.create_default_context(cadata=ca.decode('ascii'))
        context.minimum_version = ssl.TLSVersion.TLSv1_2
        url = urlsplit(material.origin)
        seconds = min(self._timeout, (self._campaign.expires_at - self._now()).total_seconds())
        deadline = time.monotonic() + seconds
        active = [None]
        def remaining():
            value = deadline - time.monotonic()
            if value <= 0:
                raise NativeReadHeld('Native read deadline expired')
            return value
        def stop():
            sock = active[0]
            if sock is not None:
                try:
                    sock.shutdown(socket.SHUT_RDWR)
                except OSError:
                    pass
        timer = Timer(seconds, stop)
        timer.daemon = True
        connection = None
        response = None
        timer.start()
        try:
            raw = socket.create_connection((material.connect_ip, url.port or 443), timeout=remaining())
            active[0] = raw
            raw.settimeout(remaining())
            tls = context.wrap_socket(raw, server_hostname=url.hostname, do_handshake_on_connect=False)
            active[0] = tls
            tls.settimeout(remaining())
            tls.do_handshake()
            if self._authorize().binding_digest != material.binding_digest:
                raise NativeReadHeld('Native credential rotated during TLS connection')
            tls.settimeout(remaining())
            connection = http.client.HTTPConnection(url.hostname, url.port or 443,
                                                     timeout=remaining())
            connection.auto_open = 0  # Never reconnect or fall back to an unverified plaintext socket.
            connection.sock = tls
            connection.request('GET', path, headers={
                'vmware-api-session-id': material.token, 'Accept': 'application/json',
                'Accept-Encoding': 'identity', 'Connection': 'close'})
            response = connection.getresponse()
            remaining()
            if response.status != 200:
                # No redirects and no response-body logging, including 401/403.
                if 300 <= response.status < 400:
                    raise NativeReadHeld('Native redirects are forbidden')
                self._authorize()
                remaining()
                return RestResponse(response.status, None)
            lengths = response.headers.get_all('Content-Length', [])
            transfers = response.headers.get_all('Transfer-Encoding', [])
            types = response.headers.get_all('Content-Type', [])
            encodings = response.headers.get_all('Content-Encoding', [])
            if (len(lengths) > 1 or lengths and (not lengths[0].isascii()
                    or not lengths[0].isdigit() or int(lengths[0]) > self._max_bytes)
                    or len(transfers) > 1 or transfers and transfers[0].lower() != 'chunked'
                    or lengths and transfers or len(types) != 1
                    or types[0].split(';', 1)[0].strip().lower() != 'application/json'
                    or len(encodings) > 1 or encodings and encodings[0].lower() != 'identity'):
                raise NativeReadHeld('Native response framing or content type is invalid')
            body = response.read(self._max_bytes + 1)
            remaining()
            if lengths and len(body) != int(lengths[0]):
                raise NativeReadHeld('Native response was truncated')
            value = decode_json(body, self._max_bytes)
            if self._authorize().binding_digest != material.binding_digest:
                raise NativeReadHeld('Native credential rotated during response')
            remaining()
            if path in self._list_paths:
                if not isinstance(value, list) or len(value) >= 4000:
                    raise NativeReadHeld('Native list is malformed or potentially truncated')
                ids = [row.get('vm') for row in value if isinstance(row, dict)]
                if (len(ids) != len(value) or any(not isinstance(vm, str)
                        or not re.fullmatch(r'vm-[1-9][0-9]{0,15}', vm) for vm in ids)
                        or len(set(ids)) != len(ids)
                        or len(self._seen_vms | set(ids)) > self._campaign.max_objects):
                    raise NativeReadHeld('Native list identity or budget is invalid')
                self._seen_vms.update(ids)
            return RestResponse(200, value)
        finally:
            timer.cancel()
            # A partial HTTPResponse owns a buffered socket reader independently
            # of HTTPConnection.sock. Close it on framing/parser/deadline holds
            # as well as success; closing only the socket leaves that reader live.
            if response is not None:
                response.close()
            if connection is not None:
                connection.close()
            if active[0] is not None:
                active[0].close()
            timer.join()
