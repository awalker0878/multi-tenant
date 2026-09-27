"""Immutable, fail-closed records for one exact-scope read-only discovery run.

These values are not proof that a campaign was approved or that a collector is
trusted. The site service must independently verify its campaign authority,
read-only platform credential, collector identity, and result provenance before
it uses this model. In particular a B10 job grant or native owner lease is not
a brownfield inventory authorization. No record here grants execution rights.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Literal

from provisioner.controlplane.authority.model import PlanScope


_ID = re.compile(r'^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$')
_FIELD = re.compile(r'^[A-Za-z][A-Za-z0-9._:-]{0,127}$')
_KINDS = frozenset({'vm', 'disk', 'nic', 'volume', 'dataset', 'image', 'network', 'pool',
                    'cluster', 'host', 'datastore', 'quota'})
_FAMILIES = frozenset({'vmware', 'nutanix', 'openstack'})
_UNKNOWN_REASONS = frozenset({'MISSING_PRIVILEGE', 'NOT_RETURNED',
                              'NOT_SUPPORTED', 'COLLECTION_ERROR', 'UNAVAILABLE'})


def _utc(value: datetime) -> bool:
    return (isinstance(value, datetime) and value.tzinfo is not None
            and value.utcoffset() == timedelta(0))


def _id(value: str) -> bool:
    return isinstance(value, str) and _ID.fullmatch(value) is not None


def _scope(scope: PlanScope) -> bool:
    return (isinstance(scope, PlanScope)
            and scope.platform_family in _FAMILIES
            and all(_id(value) for value in (
                scope.organization_id, scope.tenant_id, scope.site_id,
                scope.security_domain_id, scope.endpoint_id))
            and isinstance(scope.native_scope_id, str)
            and 1 <= len(scope.native_scope_id) <= 512
            and bool(scope.native_scope_id.strip())
            and all(ord(char) >= 32 and ord(char) != 127
                    for char in scope.native_scope_id))


def _unique_pairs(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for name, value in pairs:
        if name in result:
            raise ValueError('Duplicate JSON key')
        result[name] = value
    return result


def _nonfinite(_value: str) -> None:
    raise ValueError('Nonfinite discovery fact')


def _json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=True, allow_nan=False)


def _digest(value: object) -> str:
    return hashlib.sha256(_json(value).encode('utf-8')).hexdigest()


def _cursor(value: str | None) -> bool:
    # Native continuation tokens stay opaque; never parse or place them in a URL.
    return (value is None or isinstance(value, str)
            and 1 <= len(value) <= 2048
            and all(ord(char) >= 32 and ord(char) != 127 for char in value))


@dataclass(frozen=True, slots=True)
class DiscoveryCampaignAuthorization:
    """Bounded campaign description; the caller must verify its issuer first.

    This is intentionally independent of job grants, plans, native ownership,
    and mutation epochs. It authorizes no operation by itself.
    """

    campaign_id: str
    scope: PlanScope
    authority_reference: str
    collector_id: str
    allowed_kinds: tuple[str, ...]
    issued_at: datetime
    expires_at: datetime
    max_pages: int
    max_objects: int
    max_page_size: int

    def __post_init__(self) -> None:
        if (not _id(self.campaign_id) or not _scope(self.scope)
                or not _id(self.authority_reference) or not _id(self.collector_id)
                or not isinstance(self.allowed_kinds, tuple)
                or not self.allowed_kinds
                or any(not isinstance(kind, str) or kind not in _KINDS
                       for kind in self.allowed_kinds)
                or len(set(self.allowed_kinds)) != len(self.allowed_kinds)
                or not _utc(self.issued_at) or not _utc(self.expires_at)
                or not self.issued_at < self.expires_at
                or self.expires_at - self.issued_at > timedelta(hours=1)
                or type(self.max_pages) is not int or not 1 <= self.max_pages <= 1000
                or type(self.max_objects) is not int or not 1 <= self.max_objects <= 100000
                or type(self.max_page_size) is not int
                or not 1 <= self.max_page_size <= 500):
            raise ValueError('Invalid exact-scope discovery campaign bounds')

    def digest(self) -> str:
        """Bind the exact issuer reference, site route and read budgets."""
        return _digest(dict(format='hosting-discovery-campaign/1',
                            campaignId=self.campaign_id,
                            scope=_scope_json(self.scope),
                            authorityReference=self.authority_reference,
                            collectorId=self.collector_id,
                            allowedKinds=sorted(self.allowed_kinds),
                            issuedAt=self.issued_at.isoformat(),
                            expiresAt=self.expires_at.isoformat(),
                            maxPages=self.max_pages,
                            maxObjects=self.max_objects,
                            maxPageSize=self.max_page_size))


@dataclass(frozen=True, slots=True)
class NativeIdentity:
    endpoint_id: str
    native_scope_id: str
    platform_family: str
    resource_kind: str
    native_id: str

    def __post_init__(self) -> None:
        if (not _id(self.endpoint_id)
                or not isinstance(self.native_scope_id, str)
                or not 1 <= len(self.native_scope_id) <= 512
                or not self.native_scope_id.strip()
                or any(ord(char) < 32 or ord(char) == 127
                       for char in self.native_scope_id)
                or not isinstance(self.platform_family, str)
                or self.platform_family not in _FAMILIES
                or not isinstance(self.resource_kind, str)
                or self.resource_kind not in _KINDS
                or not isinstance(self.native_id, str)
                or not 1 <= len(self.native_id) <= 512
                or not self.native_id.strip()
                or any(ord(char) < 32 or ord(char) == 127
                       for char in self.native_id)):
            raise ValueError('Invalid immutable native identity')

    def key(self) -> tuple[str, str, str, str, str]:
        return (self.endpoint_id, self.native_scope_id, self.platform_family,
                self.resource_kind, self.native_id)


@dataclass(frozen=True, slots=True)
class DiscoveryFact:
    """A JSON fact is stored as canonical text, so nested values cannot mutate."""

    name: str
    state: Literal['KNOWN', 'UNKNOWN']
    value_json: str | None = None
    reason: str | None = None
    required_privilege: str | None = None

    @classmethod
    def known(cls, name: str, value: object) -> DiscoveryFact:
        return cls(name, 'KNOWN', _json(value))

    @classmethod
    def unknown(cls, name: str, reason: str, *,
                required_privilege: str | None = None) -> DiscoveryFact:
        return cls(name, 'UNKNOWN', reason=reason,
                   required_privilege=required_privilege)

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not _FIELD.fullmatch(self.name):
            raise ValueError('Invalid discovery fact name')
        if self.state == 'KNOWN':
            if (not isinstance(self.value_json, str)
                    or len(self.value_json.encode('utf-8')) > 8192
                    or self.reason is not None or self.required_privilege is not None):
                raise ValueError('Known fact must have only a bounded value')
            try:
                value = json.loads(self.value_json, object_pairs_hook=_unique_pairs,
                                   parse_constant=_nonfinite)
                if _json(value) != self.value_json:
                    raise ValueError('Fact must use canonical JSON')
            except (TypeError, ValueError, OverflowError) as exc:
                raise ValueError('Invalid canonical fact') from exc
        elif self.state == 'UNKNOWN':
            if (self.value_json is not None or self.reason not in _UNKNOWN_REASONS
                    or (self.reason == 'MISSING_PRIVILEGE') !=
                    (self.required_privilege is not None)
                    or self.required_privilege is not None
                    and (not isinstance(self.required_privilege, str)
                         or not _FIELD.fullmatch(self.required_privilege))):
                raise ValueError('Unknown fact needs an exact reason and privilege')
        else:
            raise ValueError('Invalid discovery fact state')

    def value(self) -> object:
        if self.state != 'KNOWN':
            raise ValueError('Unknown fact has no value')
        return json.loads(self.value_json)


@dataclass(frozen=True, slots=True)
class DiscoveryObject:
    identity: NativeIdentity
    facts: tuple[DiscoveryFact, ...]

    def __post_init__(self) -> None:
        if (not isinstance(self.identity, NativeIdentity)
                or not isinstance(self.facts, tuple) or not self.facts
                or len(self.facts) > 64
                or any(not isinstance(fact, DiscoveryFact) for fact in self.facts)
                or len({fact.name for fact in self.facts}) != len(self.facts)):
            raise ValueError('Object requires distinct bounded observed facts')


@dataclass(frozen=True, slots=True)
class DiscoveryPage:
    campaign_id: str
    scope: PlanScope
    page_number: int
    requested_cursor: str | None
    next_cursor: str | None
    collected_at: datetime
    objects: tuple[DiscoveryObject, ...]
    terminal_completeness: Literal['COMPLETE', 'PARTIAL', 'UNKNOWN'] | None = None
    collection_errors: tuple[str, ...] = ()
    missing_privileges: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if (not _id(self.campaign_id) or not _scope(self.scope)
                or type(self.page_number) is not int or self.page_number < 1
                or not _cursor(self.requested_cursor) or not _cursor(self.next_cursor)
                or self.next_cursor is not None
                and self.next_cursor == self.requested_cursor
                or not _utc(self.collected_at)
                or not isinstance(self.objects, tuple)
                or any(not isinstance(obj, DiscoveryObject) for obj in self.objects)
                or not isinstance(self.collection_errors, tuple)
                or not isinstance(self.missing_privileges, tuple)
                or len(self.collection_errors) > 64
                or len(self.missing_privileges) > 64
                or any(not _id(error) for error in self.collection_errors)
                or any(not isinstance(p, str) or not _FIELD.fullmatch(p)
                       for p in self.missing_privileges)
                or len(set(self.collection_errors)) != len(self.collection_errors)
                or len(set(self.missing_privileges)) != len(self.missing_privileges)
                or ((self.next_cursor is None) !=
                    (self.terminal_completeness is not None))
                or self.terminal_completeness not in
                    (None, 'COMPLETE', 'PARTIAL', 'UNKNOWN')):
            raise ValueError('Invalid discovery page or terminal marker')
        if (len({obj.identity.key() for obj in self.objects}) != len(self.objects)
                or any(not _matches(self.scope, obj.identity) for obj in self.objects)):
            raise ValueError('Duplicate or cross-scope native object')
        needs = {fact.required_privilege
                 for obj in self.objects for fact in obj.facts
                 if fact.reason == 'MISSING_PRIVILEGE'}
        if not needs <= set(self.missing_privileges):
            raise ValueError('Missing native read privilege was not reported')


def _matches(scope: PlanScope, identity: NativeIdentity) -> bool:
    return (scope.endpoint_id, scope.native_scope_id, scope.platform_family) == (
        identity.endpoint_id, identity.native_scope_id,
        identity.platform_family)


def _scope_json(scope: PlanScope) -> dict:
    return dict(organizationId=scope.organization_id, tenantId=scope.tenant_id,
                locationId=scope.site_id,
                securityDomainId=scope.security_domain_id,
                endpointId=scope.endpoint_id, nativeScopeId=scope.native_scope_id,
                platformFamily=scope.platform_family)


def _object_json(obj: DiscoveryObject) -> dict:
    return {'binding': dict(zip(('endpointId', 'nativeScopeId',
                                 'platformFamily', 'resourceKind', 'nativeId'),
                                obj.identity.key())),
            'facts': [dict(name=fact.name, state=fact.state,
                           value=json.loads(fact.value_json)
                           if fact.state == 'KNOWN' else None,
                           reason=fact.reason,
                           requiredPrivilege=fact.required_privilege)
                      for fact in sorted(obj.facts, key=lambda fact: fact.name)]}


@dataclass(frozen=True, slots=True)
class DiscoveryResult:
    campaign_id: str
    authorization_digest: str
    scope: PlanScope
    captured_at: datetime
    completeness: Literal['COMPLETE', 'PARTIAL', 'UNKNOWN']
    objects: tuple[DiscoveryObject, ...]
    collection_errors: tuple[str, ...]
    missing_privileges: tuple[str, ...]
    digest: str = field(init=False)

    def __post_init__(self) -> None:
        if (not _id(self.campaign_id)
                or not isinstance(self.authorization_digest, str)
                or re.fullmatch(r'[0-9a-f]{64}', self.authorization_digest) is None
                or not _scope(self.scope)
                or not _utc(self.captured_at)
                or self.completeness not in ('COMPLETE', 'PARTIAL', 'UNKNOWN')
                or not isinstance(self.objects, tuple)
                or any(not isinstance(obj, DiscoveryObject)
                       or not _matches(self.scope, obj.identity)
                       for obj in self.objects)
                or len({obj.identity.key() for obj in self.objects})
                != len(self.objects)
                or not isinstance(self.collection_errors, tuple)
                or not isinstance(self.missing_privileges, tuple)
                or len(self.collection_errors) > 64
                or len(self.missing_privileges) > 64
                or any(not _id(error) for error in self.collection_errors)
                or any(not isinstance(p, str) or not _FIELD.fullmatch(p)
                       for p in self.missing_privileges)
                or self.completeness == 'COMPLETE' and (
                    self.collection_errors or self.missing_privileges
                    or any(fact.state == 'UNKNOWN' for obj in self.objects
                           for fact in obj.facts))
                or self.completeness == 'PARTIAL' and not (
                    self.collection_errors or self.missing_privileges
                    or any(fact.state == 'UNKNOWN' for obj in self.objects
                           for fact in obj.facts))):
            raise ValueError('Invalid immutable discovery result')
        payload = dict(format='hosting-discovery-result/1',
                       campaignId=self.campaign_id,
                       authorizationDigest=self.authorization_digest,
                       scope=_scope_json(self.scope),
                       capturedAt=self.captured_at.isoformat(),
                       completeness=self.completeness,
                       objects=[_object_json(obj) for obj in sorted(
                           self.objects, key=lambda obj: obj.identity.key())],
                       collectionErrors=list(self.collection_errors),
                       missingPrivileges=list(self.missing_privileges))
        object.__setattr__(self, 'digest', _digest(payload))


def assemble_discovery_result(
    campaign: DiscoveryCampaignAuthorization,
    pages: tuple[DiscoveryPage, ...], *, checked_at: datetime,
) -> DiscoveryResult:
    """Check a complete page chain against an independently authorized run.

    `checked_at` comes from the trusted ingest service. A failed/incomplete
    enumeration stays PARTIAL or UNKNOWN and never creates tombstones by itself.
    """
    if (not isinstance(campaign, DiscoveryCampaignAuthorization)
            or not isinstance(pages, tuple) or not pages
            or any(not isinstance(page, DiscoveryPage) for page in pages)
            or not _utc(checked_at)
            or not campaign.issued_at <= checked_at < campaign.expires_at
            or len(pages) > campaign.max_pages):
        raise ValueError('Invalid or expired discovery campaign/page set')
    expected_cursor = None
    previous_time = campaign.issued_at
    seen_cursors: set[str | None] = set()
    identities: set[tuple[str, str, str, str, str]] = set()
    objects: list[DiscoveryObject] = []
    errors: set[str] = set()
    privileges: set[str] = set()
    unknown = False
    for number, page in enumerate(pages, 1):
        if (page.campaign_id != campaign.campaign_id or page.scope != campaign.scope
                or page.page_number != number
                or page.requested_cursor != expected_cursor
                or page.requested_cursor in seen_cursors
                or not previous_time <= page.collected_at <= checked_at
                or page.collected_at >= campaign.expires_at
                or len(page.objects) > campaign.max_page_size
                or (number < len(pages) and page.terminal_completeness is not None)
                or (number == len(pages) and page.terminal_completeness is None)):
            raise ValueError('Discovery page chain or budget is invalid')
        seen_cursors.add(page.requested_cursor)
        previous_time = page.collected_at
        expected_cursor = page.next_cursor
        for obj in page.objects:
            identity = obj.identity.key()
            if identity in identities or obj.identity.resource_kind not in campaign.allowed_kinds:
                raise ValueError('Duplicate or unauthorized discovered identity')
            identities.add(identity)
            objects.append(obj)
            unknown |= any(fact.state == 'UNKNOWN' for fact in obj.facts)
        if len(objects) > campaign.max_objects:
            raise ValueError('Discovery object budget exceeded')
        errors.update(page.collection_errors)
        privileges.update(page.missing_privileges)
    completeness = pages[-1].terminal_completeness
    if completeness == 'COMPLETE' and (errors or privileges or unknown):
        raise ValueError('Incomplete inventory cannot claim COMPLETE')
    if completeness == 'PARTIAL' and not (errors or privileges or unknown):
        raise ValueError('PARTIAL inventory requires a concrete gap')
    return DiscoveryResult(campaign.campaign_id, campaign.digest(), campaign.scope,
                           pages[-1].collected_at, completeness,
                           tuple(objects), tuple(sorted(errors)),
                           tuple(sorted(privileges)))
