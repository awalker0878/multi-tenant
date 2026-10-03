"""Bounded VMware VM enumeration over a trusted, injected page reader.

The reader must be bound by the site worker to the exact endpoint and native
scope, use a read-only credential and turn native permission, transport and
pagination failures into errors. Its wire API is deliberately not assumed here:
the existing vSphere reader (`provisioner/execution/vsphere_observe.py`) reads exact VM IDs,
not collection pages. This collector never opens a connection or obtains a
credential. A terminal cursor establishes only that the reader finished its
page chain; it is not independent inventory completeness or site qualification.
"""
from __future__ import annotations

import hashlib
import json
import re
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable

from provisioner.controlplane.authority.model import PlanScope

_MOID = re.compile(r'vm-[1-9][0-9]{0,15}\Z')
_UUID = re.compile(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\Z')
_CURSOR = re.compile(r'[\x21-\x7e]{1,1024}\Z')
_MAX_PAGE_SIZE = 500
_MAX_PAGES = 2000
_MAX_RECORDS = 100000
_MAX_SECONDS = 120


class EnumerationHeld(ValueError):
    """A partial, ambiguous or changed page chain cannot be published."""


@dataclass(frozen=True)
class VmSummary:
    moid: str
    instance_uuid: str
    name: str


@dataclass(frozen=True)
class VmPage:
    """Normalized adapter output; `cursor` echoes the requested cursor.

    `reported_total` is optional. If the native collection provides a count,
    the adapter must return it on every page. It must never synthesize a count.
    """

    scope: PlanScope
    cursor: str | None
    items: tuple[VmSummary, ...]
    next_cursor: str | None
    reported_total: int | None


@dataclass(frozen=True)
class VmGeneration:
    scope: PlanScope
    observed_at: datetime
    items: tuple[VmSummary, ...]
    pages: int
    digest: str
    page_chain_complete: bool = True
    native_qualified: bool = False
    ownership_accepted: bool = False


@dataclass(frozen=True)
class VmChange:
    kind: str  # FIRST_SEEN, RENAMED, NOT_SEEN
    moid: str
    instance_uuid: str
    previous_name: str | None
    current_name: str | None


def _valid_summary(item: VmSummary) -> None:
    if (not isinstance(item, VmSummary)
            or not isinstance(item.moid, str) or not _MOID.fullmatch(item.moid)
            or not isinstance(item.instance_uuid, str)
            or not _UUID.fullmatch(item.instance_uuid)
            or not isinstance(item.name, str) or not 1 <= len(item.name) <= 256
            or item.name != item.name.strip()
            or any(ord(char) < 32 or ord(char) == 127 for char in item.name)):
        raise EnumerationHeld('Invalid native VM identity or name')


def _digest(scope: PlanScope, items: tuple[VmSummary, ...]) -> str:
    encoded = json.dumps({
        'scope': vars(scope),
        'items': [vars(item) for item in items],
    }, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode('utf-8')
    return hashlib.sha256(encoded).hexdigest()


def enumerate_vms(scope: PlanScope,
                  fetch_page: Callable[[PlanScope, str | None, int], VmPage], *,
                  page_size: int = 250, max_pages: int = _MAX_PAGES,
                  max_records: int = _MAX_RECORDS,
                  max_seconds: int = _MAX_SECONDS) -> VmGeneration:
    """Consume every bounded page or raise without returning a partial result.

    `fetch_page` is called only with the trusted scope, cursor and page limit.
    Its own I/O timeouts must be shorter than this collector's deadline.
    """
    if (not isinstance(scope, PlanScope) or scope.platform_family != 'vmware'
            or not callable(fetch_page)
            or any(type(value) is not int or value < 1 for value in
                   (page_size, max_pages, max_records, max_seconds))
            or page_size > _MAX_PAGE_SIZE or max_pages > _MAX_PAGES
            or max_records > _MAX_RECORDS or max_seconds > _MAX_SECONDS):
        raise ValueError('Exact VMware scope and bounded enumeration required')

    deadline = time.monotonic() + max_seconds
    cursor = None
    used_cursors: set[str] = set()
    seen_moids: set[str] = set()
    seen_uuids: set[str] = set()
    observed: list[VmSummary] = []
    count: int | None = None
    for page_number in range(1, max_pages + 1):
        if time.monotonic() >= deadline:
            raise EnumerationHeld('VM enumeration deadline expired')
        try:
            page = fetch_page(scope, cursor, page_size)
        except Exception as exc:
            raise EnumerationHeld('VM page unavailable or unauthorized') from exc
        if time.monotonic() >= deadline:
            raise EnumerationHeld('VM enumeration deadline expired')
        if (not isinstance(page, VmPage) or page.scope != scope
                or page.cursor != cursor or not isinstance(page.items, tuple)
                or len(page.items) > page_size
                or (page.next_cursor is not None and
                    (not isinstance(page.next_cursor, str)
                     or not _CURSOR.fullmatch(page.next_cursor)))
                or (page.reported_total is not None and
                    (type(page.reported_total) is not int or page.reported_total < 0))):
            raise EnumerationHeld('VM page scope, cursor or shape changed')
        if count is not None and page.reported_total != count:
            raise EnumerationHeld('VM collection count changed or disappeared')
        if page_number > 1 and count is None and page.reported_total is not None:
            raise EnumerationHeld('VM collection count appeared mid-enumeration')
        if page_number == 1:
            count = page.reported_total
        if page.next_cursor is not None and not page.items:
            raise EnumerationHeld('Empty nonterminal VM page')
        for item in page.items:
            _valid_summary(item)
            if item.moid in seen_moids or item.instance_uuid in seen_uuids:
                raise EnumerationHeld('Duplicate native VM identity')
            seen_moids.add(item.moid)
            seen_uuids.add(item.instance_uuid)
            observed.append(item)
        if len(observed) > max_records:
            raise EnumerationHeld('VM record budget exceeded')
        if page.next_cursor is None:
            if count is not None and len(observed) != count:
                raise EnumerationHeld('Terminal VM count differs from collection count')
            items = tuple(sorted(observed, key=lambda item: item.moid))
            return VmGeneration(scope, datetime.now(timezone.utc), items,
                                page_number, _digest(scope, items))
        if page.next_cursor == cursor or page.next_cursor in used_cursors:
            raise EnumerationHeld('VM cursor repeated')
        used_cursors.add(page.next_cursor)
        cursor = page.next_cursor
    raise EnumerationHeld('VM page budget exhausted before a terminal cursor')


def compare_generations(previous: VmGeneration,
                        current: VmGeneration) -> tuple[VmChange, ...]:
    """Preserve identity across renames; absence is NOT_SEEN, never deletion.

    Persistence, native identity reconciliation and owner review belong to the
    control plane. These observations cannot adopt, retire or move a workload.
    """
    if (not isinstance(previous, VmGeneration) or not isinstance(current, VmGeneration)
            or previous.scope != current.scope
            or not previous.page_chain_complete or not current.page_chain_complete
            or current.observed_at <= previous.observed_at):
        raise EnumerationHeld('Comparable ordered generations required')
    before = {item.moid: item for item in previous.items}
    after = {item.moid: item for item in current.items}
    changes = []
    for moid in sorted(before.keys() | after.keys()):
        old, new = before.get(moid), after.get(moid)
        if old and new and old.instance_uuid != new.instance_uuid:
            raise EnumerationHeld('A native VM ID was reused for a different instance')
        if old and new and old.name != new.name:
            changes.append(VmChange('RENAMED', moid, old.instance_uuid,
                                    old.name, new.name))
        elif old and not new:
            changes.append(VmChange('NOT_SEEN', moid, old.instance_uuid,
                                    old.name, None))
        elif new and not old:
            changes.append(VmChange('FIRST_SEEN', moid, new.instance_uuid,
                                    None, new.name))
    old_by_uuid = {item.instance_uuid: item.moid for item in previous.items}
    if any(item.instance_uuid in old_by_uuid and old_by_uuid[item.instance_uuid] != item.moid
           for item in current.items):
        raise EnumerationHeld('An instance UUID moved to another native VM ID')
    return tuple(changes)
