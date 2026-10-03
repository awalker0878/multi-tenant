"""Actual bounded HTTPS reads for the selected vCenter discovery collector.

This is not a mutation client or an authentication fallback. The native owner
supplies an independently signed, exact-campaign session binding. The existing
signed campaign and independent read-only witness are checked around every read.
Only folder-filtered VM lists and detail IDs returned by those lists are sent.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Callable
from urllib.parse import urlencode

from .vmware_rest import (API_RELEASE, PROFILE, FolderSelection, RestResponse,
                          collect_vmware_vms)
from ..model import DiscoveryCampaignAuthorization, _id, _utc
from .vmware_credentials import SignedFileVmwareCredentialSource
from ..native_credentials import NativeReadHeld
from ..native_https import read_json
from ..read_budget import NativeReadGate, NativeReadAdmissionHeld
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
                 clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
                 read_gate: NativeReadGate | None = None):
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
        if read_gate is not None:
            if not isinstance(read_gate, NativeReadGate):
                raise TypeError('A native endpoint read gate is required')
            read_gate.require_scope(campaign.scope)
        self._read_gate = read_gate
        self._admission_failed = False
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
        except Exception as exc:
            self._admission_failed |= isinstance(exc, NativeReadAdmissionHeld)
            # Neither provider exceptions nor native error bodies enter evidence.
            raise NativeReadHeld('Verified VMware HTTPS read unavailable') from None
        finally:
            self._lock.release()

    def _get(self, path: str) -> RestResponse:
        material = self._authorize()

        def current():
            if self._authorize().binding_digest != material.binding_digest:
                raise NativeReadHeld('Native credential rotated during read')

        status, value = read_json(origin=material.origin, connect_ip=material.connect_ip,
            ca_digest=material.ca_digest, ca_bundle=self._ca, path=path,
            credential_header='vmware-api-session-id', credential=material.token,
            timeout=min(self._timeout, (self._campaign.expires_at - self._now()).total_seconds()),
            max_response_bytes=self._max_bytes, authorize=current, read_gate=self._read_gate)
        if status == 200 and path in self._list_paths:
            if not isinstance(value, list) or len(value) >= 4000:
                raise NativeReadHeld('Native list is malformed or potentially truncated')
            ids = [row.get('vm') for row in value if isinstance(row, dict)]
            if (len(ids) != len(value) or any(not isinstance(vm, str)
                    or not re.fullmatch(r'vm-[1-9][0-9]{0,15}', vm) for vm in ids)
                    or len(set(ids)) != len(ids)
                    or len(self._seen_vms | set(ids)) > self._campaign.max_objects):
                raise NativeReadHeld('Native list identity or budget is invalid')
            self._seen_vms.update(ids)
        return RestResponse(status, value)
