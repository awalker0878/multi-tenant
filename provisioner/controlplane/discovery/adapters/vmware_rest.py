"""Bounded vCenter REST VM list over an exact, externally verified folder set.

Broadcom's vSphere Automation API documents GET /api/vcenter/vm as a list of
at most 4000 *visible* VMs matching folder/datacenter filters, with no cursor.
It can therefore neither paginate a large folder nor prove that an account
can see all VMs. GET /api/vcenter/vm/{vm} supplies optional instance identity
and requires System.Read on that VM. Official API references:
https://developer.broadcom.com/xapis/vsphere-automation-api/latest/api/vcenter/vm/get/
https://developer.broadcom.com/xapis/vsphere-automation-api/latest/api/vcenter/vm/vm/get/

The caller supplies an independently reviewed list of every in-scope VM
folder and a site-bound GET transport. This module does not discover the folder
tree or verify the installed vCenter release/privilege topology. Even a good
result is only a visible, assessment-only observation; missing inherited
privileges can silently hide VMs. Use a separately qualified native inventory
enumerator and independent reconciliation before asserting completeness.
"""
from __future__ import annotations

import hashlib
import json
import re
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable
from urllib.parse import urlencode

from provisioner.controlplane.authority.model import PlanScope
from .vmware import EnumerationHeld, VmSummary, _valid_summary

API_RELEASE = '8.0.3.0'
PROFILE = 'vcenter-rest-vm-list-8.0.3.0-visible-only'
_FOLDER = re.compile(r'group-v[1-9][0-9]{0,15}\Z')
_DATACENTER = re.compile(r'datacenter-[1-9][0-9]{0,15}\Z')
_SHA256 = re.compile(r'[0-9a-f]{64}\Z')
_MAX_FOLDERS = 128
_MAX_VMS = 50000
_MAX_SECONDS = 120
_LIST_LIMIT = 4000


@dataclass(frozen=True)
class FolderSelection:
    scope: PlanScope
    folder_ids: tuple[str, ...]
    coverage_digest: str  # independently reviewed folder-tree artifact, not self-attestation
    api_release: str = API_RELEASE


@dataclass(frozen=True)
class RestResponse:
    status: int
    body: object


@dataclass(frozen=True)
class VisibleVmObservation:
    scope: PlanScope
    profile: str
    folder_ids: tuple[str, ...]
    folder_coverage_digest: str
    observed_at: datetime
    items: tuple[VmSummary, ...]
    digest: str
    status: str = 'SCOPED_VISIBLE_ONLY'
    native_qualified: bool = False
    ownership_accepted: bool = False


def _request(fetch_get: Callable, scope: PlanScope, path: str,
             deadline: float) -> object:
    if time.monotonic() >= deadline:
        raise EnumerationHeld('VM REST read deadline expired')
    try:
        response = fetch_get(scope, path, API_RELEASE)
    except Exception as exc:
        raise EnumerationHeld('VM REST read unavailable or unauthorized') from exc
    if time.monotonic() >= deadline:
        raise EnumerationHeld('VM REST read deadline expired')
    if not isinstance(response, RestResponse) or response.status != 200:
        raise EnumerationHeld('VM REST read unavailable or unauthorized')
    return response.body


def enumerate_visible_vms(selection: FolderSelection,
                          fetch_get: Callable[[PlanScope, str, str], RestResponse], *,
                          max_vms: int = _MAX_VMS,
                          max_seconds: int = _MAX_SECONDS) -> VisibleVmObservation:
    """Scan each exact folder; return nothing if any native read is inconclusive.

    The injected transport must pin TLS origin to `scope.endpoint_id`, verify
    the installed API release, enforce read-only scoped credentials, reject
    redirects, invalid JSON and oversized responses, and bound each GET below
    the deadline. None of those facts can be inferred from a REST list payload.
    A `coverage_digest` is an opaque reference to independent folder evidence;
    possession of a digest does not prove it was reviewed or exhaustive.
    """
    if (not isinstance(selection, FolderSelection)
            or not isinstance(selection.scope, PlanScope)
            or selection.scope.platform_family != 'vmware'
            or not _DATACENTER.fullmatch(selection.scope.native_scope_id)
            or selection.api_release != API_RELEASE
            or not isinstance(selection.folder_ids, tuple)
            or not 1 <= len(selection.folder_ids) <= _MAX_FOLDERS
            or any(not isinstance(folder, str) or not _FOLDER.fullmatch(folder)
                   for folder in selection.folder_ids)
            or len(set(selection.folder_ids)) != len(selection.folder_ids)
            or not isinstance(selection.coverage_digest, str)
            or not _SHA256.fullmatch(selection.coverage_digest)
            or not callable(fetch_get)
            or type(max_vms) is not int or not 1 <= max_vms <= _MAX_VMS
            or type(max_seconds) is not int or not 1 <= max_seconds <= _MAX_SECONDS):
        raise ValueError('Exact VMware release, datacenter and folder coverage required')

    deadline = time.monotonic() + max_seconds
    found: dict[str, VmSummary] = {}
    instance_ids: set[str] = set()
    for folder in selection.folder_ids:
        query = urlencode((('folders', folder),
                           ('datacenters', selection.scope.native_scope_id)))
        body = _request(fetch_get, selection.scope,
                        '/api/vcenter/vm?' + query, deadline)
        if not isinstance(body, list) or len(body) >= _LIST_LIMIT:
            # Exactly 4000 could mean a truncated visible set; the API has no
            # cursor or count to tell. A >4000 native error also holds above.
            raise EnumerationHeld('VM folder result reached unpageable API limit')
        for row in body:
            if (not isinstance(row, dict) or not isinstance(row.get('vm'), str)
                    or not re.fullmatch(r'vm-[1-9][0-9]{0,15}', row['vm'])
                    or not isinstance(row.get('name'), str)):
                raise EnumerationHeld('VM REST list identity missing')
            vm_id = row['vm']
            if vm_id in found:
                raise EnumerationHeld('VM appears in more than one reviewed folder')
            if len(found) >= max_vms:
                raise EnumerationHeld('VM REST record budget exceeded')
            detail = _request(fetch_get, selection.scope,
                              '/api/vcenter/vm/' + vm_id, deadline)
            if (not isinstance(detail, dict) or detail.get('name') != row['name']
                    or not isinstance(detail.get('identity'), dict)):
                raise EnumerationHeld('VM identity unavailable or changed during scan')
            item = VmSummary(vm_id, detail['identity'].get('instance_uuid'),
                             row['name'])
            _valid_summary(item)
            if item.instance_uuid in instance_ids:
                raise EnumerationHeld('Duplicate vCenter instance UUID')
            found[vm_id] = item
            instance_ids.add(item.instance_uuid)
    ordered = tuple(found[key] for key in sorted(found))
    encoded = json.dumps({
        'scope': vars(selection.scope), 'profile': PROFILE,
        'folders': selection.folder_ids,
        'folderCoverageDigest': selection.coverage_digest,
        'items': [vars(item) for item in ordered],
    }, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode('utf-8')
    return VisibleVmObservation(selection.scope, PROFILE, selection.folder_ids,
                                selection.coverage_digest,
                                datetime.now(timezone.utc), ordered,
                                hashlib.sha256(encoded).hexdigest())
