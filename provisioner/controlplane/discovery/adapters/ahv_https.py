"""Signed, bounded Prism VMM v4.0 VM-list reads for one admitted AHV cluster.

Only service-account API keys are supported. Account/key creation, login and
native mutations are not exposed. Successful enumeration does not establish
independent native visibility or grant migration authority.
"""
from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Callable, Mapping
from urllib.parse import urlencode

from .ahv import API_VERSION, COLLECTOR_ID, VM_PATH, _uuid, collect_ahv_vms
from .ahv_credentials import SignedFileAhvCredentialSource
from ..model import DiscoveryCampaignAuthorization, _id, _utc
from ..native_credentials import NativeReadHeld
from ..native_https import read_json
from ..read_budget import NativeReadGate, NativeReadAdmissionHeld
from ..trust import BoundDiscoveryIngestVerifier


class AhvHttpsTransport:
    """Serial exact-page reads using independently attested native credentials.

    There is no user-selected filter or server URL following. Every attempted
    request consumes the campaign budget. A transport/HTTP failure latches the
    instance closed, so a caller cannot accidentally retry ambiguous reads.
    A newly admitted campaign is needed after failure or exhaustion.
    """
    def __init__(self, campaign: DiscoveryCampaignAuthorization, environment_id: str, *,
                 verifier: BoundDiscoveryIngestVerifier,
                 credentials: SignedFileAhvCredentialSource, ca_bundle: str | Path,
                 timeout: float = 5.0, max_response_bytes: int = 4 * 1024 * 1024,
                 clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
                 read_gate: NativeReadGate | None = None):
        if (not isinstance(campaign, DiscoveryCampaignAuthorization)
                or campaign.scope.platform_family != 'nutanix'
                or campaign.collector_id != COLLECTOR_ID or campaign.allowed_kinds != ('vm',)
                or _uuid(campaign.scope.native_scope_id) != campaign.scope.native_scope_id
                or not _id(environment_id) or not isinstance(verifier, BoundDiscoveryIngestVerifier)
                or not isinstance(credentials, SignedFileAhvCredentialSource)
                or type(timeout) not in (int, float) or not 0 < timeout <= 15
                or type(max_response_bytes) is not int or not 1024 <= max_response_bytes <= 4*1024*1024
                or not callable(clock)):
            raise ValueError('Exact AHV campaign and bounded native read configuration required')
        self._campaign, self._environment = campaign, environment_id
        self._verifier, self._credentials, self._ca = verifier, credentials, Path(ca_bundle)
        if read_gate is not None:
            if not isinstance(read_gate, NativeReadGate):
                raise TypeError('A native endpoint read gate is required')
            read_gate.require_scope(campaign.scope)
        self._read_gate = read_gate
        self._admission_failed = False
        self._timeout, self._max_bytes, self._clock = timeout, max_response_bytes, clock
        self._last_time = campaign.issued_at
        self._lock = Lock()
        self._requests = 0
        self._failed = False
        self._page_size = min(campaign.max_page_size, 100, campaign.max_objects)
        self._filter = f"cluster/extId eq '{campaign.scope.native_scope_id}'"

    @property
    def scope(self):
        return self._campaign.scope

    @property
    def api_version(self):
        return API_VERSION

    @property
    def read_only(self):
        return True  # Local GET restriction; native privileges are independently witnessed.

    def _now(self):
        if self._read_gate is not None:
            self._read_gate.check()
        if self._admission_failed:
            raise NativeReadAdmissionHeld('Native read admission did not complete')
        now = self._clock()
        if not _utc(now) or not self._last_time <= now < self._campaign.expires_at:
            raise NativeReadHeld('Native read campaign expired or clock regressed')
        self._last_time = now
        return now

    def _authorize(self):
        now = self._now()
        material = self._credentials.read(self._campaign, self._environment, checked_at=now)
        self._verifier.verify_read_credential(self._campaign, self._environment, now,
            material.credential_reference, self._credentials.authority_public_key)
        self._now()
        return material

    def collect(self):
        # Do not let the pure parser's error-to-UNKNOWN path swallow revocation.
        try:
            if self._requests or self._failed:
                raise NativeReadHeld('Use a fresh admitted campaign after collection')
            self._authorize()
            pages = collect_ahv_vms(self._campaign, self, clock=self._now)
            self._authorize()
            last = pages[-1]
            if last.terminal_completeness in ('COMPLETE', 'PARTIAL'):
                # A returned total accounts for the visible page set, not for
                # objects hidden by native RBAC or unobserved scope drift.
                pages = (*pages[:-1], replace(last, terminal_completeness='PARTIAL',
                    collection_errors=(*last.collection_errors, 'VISIBLE_INVENTORY_ONLY')))
            return pages
        except Exception:
            raise NativeReadHeld('Verified AHV campaign collection unavailable') from None

    def get(self, path: str, *, params: Mapping[str, str | int]) -> tuple[int, object]:
        if not self._lock.acquire(timeout=self._timeout):
            raise NativeReadHeld('Native discovery read is already active')
        try:
            if (self._failed or self._requests >= self._campaign.max_pages or path != VM_PATH
                    or not isinstance(params, dict) or set(params) != {'$page', '$limit', '$filter'}
                    or type(params['$page']) is not int or params['$page'] != self._requests
                    or type(params['$limit']) is not int or params['$limit'] != self._page_size
                    or params['$filter'] != self._filter):
                raise NativeReadHeld('Native read path, page or scope is not admitted')
            # Copy exact canonical values; never forward a caller/server mapping.
            query = urlencode((('$page', self._requests), ('$limit', self._page_size),
                               ('$filter', self._filter)))
            self._requests += 1
            material = self._authorize()

            def current():
                if self._authorize().binding_digest != material.binding_digest:
                    raise NativeReadHeld('Native credential rotated during read')

            status, body = read_json(origin=material.origin, connect_ip=material.connect_ip,
                ca_digest=material.ca_digest, ca_bundle=self._ca, path=VM_PATH + '?' + query,
                credential_header='X-Ntnx-Api-Key', credential=material.api_key,
                timeout=min(self._timeout, (self._campaign.expires_at - self._now()).total_seconds()),
                max_response_bytes=self._max_bytes, authorize=current, read_gate=self._read_gate)
            if status != 200:
                self._failed = True
            return status, body
        except Exception as exc:
            self._admission_failed |= isinstance(exc, NativeReadAdmissionHeld)
            self._failed = True
            raise NativeReadHeld('Verified AHV HTTPS read unavailable') from None
        finally:
            self._lock.release()
