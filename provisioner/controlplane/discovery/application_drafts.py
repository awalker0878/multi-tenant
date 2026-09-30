"""Append-only application proposals, not accepted ownership or migration plans.

The API supplies a live authorization callback and authenticated audit identity.
Native facts come only from the stored, digest-verified discovery generation.
Saving a proposal never calls the reviewed-candidate API or grants execution.
"""
from __future__ import annotations

import hashlib
import json
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from typing import Callable

from provisioner.controlplane.authority.model import PlanScope
from provisioner.controlplane.persistence.store import AuditContext, TenantContext
from .grouping import (ConsistencyProposal, DependencyAssertion, GroupDraft, GroupMember,
                       proposal_document, validate_draft)
from .model import NativeIdentity, _id, _json, _utc
from .native_credentials import decode_json
from .normalization import hydrate_generation
from .persistence import DiscoveryRepository, StoredObservation
from .trust import _keys, _time

MAX_DRAFT_BYTES = 131072
_MAX = 2**63 - 1
_COLUMNS = ('application_group_id, revision, generation, result_digest, proposal_json, '
            'proposal_digest, recorded_by, recorded_at, record_digest')
_SCOPE_SQL = ('organization_id=%s AND tenant_id=%s AND environment_id=%s AND site_id=%s '
              'AND security_domain_id=%s AND endpoint_id=%s AND native_scope_id=%s AND platform_family=%s')


class ApplicationDraftConflict(RuntimeError):
    """Selected proposal revision or source generation is no longer current."""


def _digest(value):
    return hashlib.sha256(_json(value).encode('ascii')).hexdigest()


def _sha(value):
    return isinstance(value, str) and len(value) == 64 and all(c in '0123456789abcdef' for c in value)


def _array(value, maximum):
    if not isinstance(value, list) or len(value) > maximum:
        raise ValueError('A bounded proposal array is required')
    return value


def parse_content(document: dict) -> tuple[GroupDraft, tuple[DependencyAssertion, ...]]:
    """Decode only proposal fields; client-supplied review/authority is forbidden."""
    value = _keys(document, {'draft', 'dependencies'})
    draft = _keys(value['draft'], {'applicationGroupId', 'name', 'ownerId', 'members',
        'datasetIds', 'consistencyGroups', 'startupOrder'})
    members = []
    for item in _array(draft['members'], 100):
        member = _keys(item, {'workloadId', 'nativeVm'})
        identity = _array(member['nativeVm'], 5)
        if len(identity) != 5:
            raise ValueError('An exact native VM identity is required')
        members.append(GroupMember(member['workloadId'], NativeIdentity(*identity)))
    groups = []
    for item in _array(draft['consistencyGroups'], 100):
        group = _keys(item, {'groupId', 'datasetIds'})
        groups.append(ConsistencyProposal(group['groupId'], tuple(_array(group['datasetIds'], 1000))))
    edges = []
    for item in _array(value['dependencies'], 500):
        edge = _keys(item, {'assertionId', 'sourceWorkloadId', 'targetWorkloadId', 'relation',
                           'state', 'source', 'sourceReference', 'observedAt', 'unknownReason'})
        edges.append(DependencyAssertion(edge['assertionId'], edge['sourceWorkloadId'],
            edge['targetWorkloadId'], edge['relation'], edge['state'], edge['source'],
            edge['sourceReference'], _time(edge['observedAt']), edge['unknownReason']))
    return GroupDraft(draft['applicationGroupId'], draft['name'], draft['ownerId'],
        tuple(members), tuple(_array(draft['datasetIds'], 1000)), tuple(groups),
        tuple(_array(draft['startupOrder'], 100))), tuple(edges)


@dataclass(frozen=True, slots=True)
class StoredApplicationDraft:
    environment_id: str
    scope: PlanScope
    application_group_id: str
    revision: int
    generation: int
    result_digest: str
    proposal_json: str
    proposal_digest: str
    recorded_by: str
    recorded_at: datetime
    record_digest: str

    def binding(self) -> dict:
        return {'format': 'hosting-application-draft-revision/1',
            'environmentId': self.environment_id, 'scope': vars(self.scope),
            'applicationGroupId': self.application_group_id, 'revision': self.revision,
            'generation': self.generation, 'resultDigest': self.result_digest,
            'proposalDigest': self.proposal_digest, 'recordedBy': self.recorded_by,
            'recordedAt': self.recorded_at.isoformat()}

    def document(self, *, latest_generation: int) -> dict:
        return {**self.binding(), 'recordDigest': self.record_digest,
                'proposal': json.loads(self.proposal_json), 'status': 'UNREVIEWED',
                'latestGeneration': latest_generation,
                'sourceSuperseded': latest_generation != self.generation,
                'ownershipAccepted': False, 'executionAuthorized': False}


    def summary(self, *, latest_generation: int) -> dict:
        """A verified revision summary, not another stored proposal or approval."""
        value = self.document(latest_generation=latest_generation)
        proposal = value.pop('proposal')
        draft, edges = proposal['draft'], proposal['dependencies']
        return {**value, 'name': draft['name'], 'ownerId': draft['ownerId'],
                'memberCount': len(draft['members']), 'datasetCount': len(draft['datasetIds']),
                'dependencyCount': len(edges),
                'unknownDependencyCount': sum(edge['state'] == 'UNKNOWN' for edge in edges)}


class ApplicationDraftRepository:
    """Trusted service storage; runtime SQL role needs explicit SELECT/INSERT only."""
    def __init__(self, connection_factory: Callable):
        if not callable(connection_factory):
            raise TypeError('A transactional PostgreSQL connection is required')
        self._connect = connection_factory

    @contextmanager
    def _session(self, ctx, scope, environment_id, authorize):
        DiscoveryRepository._require_scope(ctx, scope, environment_id)
        if not callable(authorize):
            raise TypeError('Live exact-scope authorization is required')
        with self._connect() as connection:
            if connection.autocommit:
                raise RuntimeError('Application drafts require transactional access')
            role = connection.execute('SELECT rolsuper, rolbypassrls FROM pg_catalog.pg_roles '
                                      'WHERE rolname=current_user').fetchone()
            if not role or role[0] or role[1] or connection.execute(
                    'SELECT hosting_controlplane.is_site_worker_role()').fetchone()[0]:
                raise PermissionError('Application drafts require a non-worker RLS role')
            connection.execute("SELECT set_config('app.organization_id',%s,true), "
                "set_config('app.tenant_id',%s,true), set_config('TimeZone','UTC',true), "
                "set_config('lock_timeout','5s',true), "
                "set_config('statement_timeout','10s',true)", (ctx.organization_id, ctx.tenant_id))
            authorize(scope, connection.execute('SELECT clock_timestamp()').fetchone()[0])
            yield connection

    @staticmethod
    def _row(environment_id, scope, row):
        stored = StoredApplicationDraft(environment_id, scope, *row)
        body = _keys(decode_json(stored.proposal_json.encode('ascii'), MAX_DRAFT_BYTES),
                     {'format', 'discoveryDigest', 'scope', 'draft', 'dependencies'})
        parse_content({'draft': body['draft'], 'dependencies': body['dependencies']})
        if (body['format'] != 'hosting-application-group-candidate/1'
                or body['discoveryDigest'] != stored.result_digest or body['scope'] != vars(scope)
                or body['draft']['applicationGroupId'] != stored.application_group_id
                or _json(body) != stored.proposal_json or _digest(body) != stored.proposal_digest
                or not _utc(stored.recorded_at) or _digest(stored.binding()) != stored.record_digest):
            raise ValueError('Stored proposal identity or content has changed')
        return stored

    @staticmethod
    def _snapshot(connection, args, generation, result_digest):
        row = connection.execute('SELECT generation, campaign_id, authorization_digest, result_digest, '
            'captured_at, completeness, collection_errors, missing_privileges, object_count '
            'FROM hosting_controlplane.discovery_generations WHERE '+_SCOPE_SQL+
            ' ORDER BY generation DESC LIMIT 1', args).fetchone()
        if row is None or row[0] != generation or row[3] != result_digest:
            raise ApplicationDraftConflict('A current pinned source generation is required')
        scope = PlanScope(args[0], args[1], *args[3:])
        metadata = DiscoveryRepository._generation_row(args[2], scope, row)
        rows = connection.execute('SELECT resource_kind, native_id, facts_json, object_digest '
            'FROM hosting_controlplane.discovery_observations WHERE organization_id=%s AND tenant_id=%s '
            'AND environment_id=%s AND generation=%s ORDER BY resource_kind, native_id LIMIT 100001',
            (*args[:3], generation)).fetchall()
        observations = tuple(StoredObservation(generation,
            NativeIdentity(scope.endpoint_id, scope.native_scope_id, scope.platform_family, kind, native_id),
            tuple(json.loads(facts)), digest) for kind, native_id, facts, digest in rows)
        return hydrate_generation(metadata, observations)

    def save(self, ctx: TenantContext, scope: PlanScope, environment_id: str, *, generation: int,
             result_digest: str, content: dict, expected_revision: int, audit: AuditContext,
             authorize: Callable) -> StoredApplicationDraft:
        if (type(generation) is not int or not 1 <= generation <= _MAX
                or type(expected_revision) is not int or not 0 <= expected_revision < _MAX
                or not _sha(result_digest) or not isinstance(audit, AuditContext)):
            raise ValueError('Exact generation, revision, digest and authenticated actor are required')
        # Freeze caller content before transactions/callbacks. Unknown and duplicate
        # wire fields are rejected by the HTTP decoder and this closed parser.
        raw = _json(content).encode('ascii')
        if len(raw) > MAX_DRAFT_BYTES:
            raise ValueError('Application proposal exceeds its aggregate bound')
        content = decode_json(raw, MAX_DRAFT_BYTES)
        draft, dependencies = parse_content(content)
        # Normalize accepted UTC spellings before comparing an exact retry.
        for item, edge in zip(content['dependencies'], dependencies):
            item['observedAt'] = edge.observed_at.isoformat()
        if not _id(draft.application_group_id):
            raise ValueError('An exact application proposal identity is required')
        DiscoveryRepository._require_scope(ctx, scope, environment_id)
        args = DiscoveryRepository._scope_args(ctx, scope, environment_id)
        with self._session(ctx, scope, environment_id, authorize) as connection:
            # Same lock as native generation publication: a newer source cannot
            # arrive between the currency check and this draft's commit.
            key = hashlib.sha256(_json(args).encode('utf-8')).digest()
            connection.execute('SELECT pg_advisory_xact_lock(%s::bigint)',
                (int.from_bytes(key[:8], 'big', signed=True),))
            at = connection.execute('SELECT clock_timestamp()').fetchone()[0]
            authorize(scope, at)
            previous = connection.execute('SELECT '+_COLUMNS+
                ' FROM hosting_controlplane.application_draft_revisions WHERE '+_SCOPE_SQL+
                ' AND application_group_id=%s ORDER BY revision DESC LIMIT 1',
                (*args, draft.application_group_id)).fetchone()
            if previous:
                old = self._row(environment_id, scope, previous)
                prior = json.loads(old.proposal_json)
                if (old.revision == expected_revision + 1 and old.recorded_by == audit.actor_id
                        and old.generation == generation and old.result_digest == result_digest
                        and {'draft': prior['draft'], 'dependencies': prior['dependencies']} == content):
                    authorize(scope, connection.execute('SELECT clock_timestamp()').fetchone()[0])
                    return old  # Lost-ACK retry retains original actor, time, and revision.
            if (previous[1] if previous else 0) != expected_revision:
                raise ApplicationDraftConflict('Application proposal revision has advanced')
            result = self._snapshot(connection, args, generation, result_digest)
            at = connection.execute('SELECT clock_timestamp()').fetchone()[0]
            validate_draft(result, draft, dependencies, checked_at=at)
            proposal = proposal_document(result, draft, dependencies)
            payload = _json(proposal)
            if len(payload.encode('ascii')) > MAX_DRAFT_BYTES:
                raise ValueError('Application proposal exceeds its aggregate bound')
            row = StoredApplicationDraft(environment_id, scope, draft.application_group_id,
                expected_revision+1, generation, result_digest, payload, _digest(proposal),
                audit.actor_id, at, '')
            record_digest = _digest(row.binding())
            connection.execute('INSERT INTO hosting_controlplane.application_draft_revisions '
                '(organization_id,tenant_id,environment_id,site_id,security_domain_id,endpoint_id,'
                'native_scope_id,platform_family,'+_COLUMNS+') VALUES ('+','.join(['%s']*17)+')',
                (*args, row.application_group_id, row.revision, generation, result_digest, payload,
                 row.proposal_digest, row.recorded_by, at, record_digest))
            connection.execute('INSERT INTO hosting_controlplane.audit_events '
                '(organization_id,tenant_id,actor_id,correlation_id,action,record_kind,record_id,'
                'revision,record_digest,details) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb)',
                (ctx.organization_id,ctx.tenant_id,audit.actor_id,audit.correlation_id,
                 'RECORD_CREATE' if expected_revision == 0 else 'RECORD_UPDATE',
                 'ApplicationDraft', draft.application_group_id,row.revision,record_digest,
                 _json({'environmentId':environment_id,'generation':generation})))
            authorize(scope, connection.execute('SELECT clock_timestamp()').fetchone()[0])
            return self._row(environment_id,scope,(row.application_group_id,row.revision,generation,
                result_digest,payload,row.proposal_digest,row.recorded_by,at,record_digest))

    def get(self, ctx: TenantContext, scope: PlanScope, environment_id: str, application_group_id: str,
            *, revision: int | None = None, authorize: Callable) -> dict | None:
        if (not _id(application_group_id) or revision is not None
                and (type(revision) is not int or not 1 <= revision <= _MAX)):
            raise ValueError('An exact proposal identity and bounded revision are required')
        DiscoveryRepository._require_scope(ctx, scope, environment_id)
        args = DiscoveryRepository._scope_args(ctx, scope, environment_id)
        with self._session(ctx,scope,environment_id,authorize) as connection:
            row = connection.execute('SELECT '+_COLUMNS+
                ' FROM hosting_controlplane.application_draft_revisions WHERE '+_SCOPE_SQL+
                ' AND application_group_id=%s'+(' AND revision=%s' if revision is not None else '')+
                ' ORDER BY revision DESC LIMIT 1',
                (*args,application_group_id,*((revision,) if revision is not None else ()))).fetchone()
            if row is None:
                return None
            stored = self._row(environment_id,scope,row)
            latest = connection.execute('SELECT max(generation) FROM '
                'hosting_controlplane.discovery_generations WHERE '+_SCOPE_SQL,args).fetchone()[0]
            if latest is None or latest < stored.generation:
                raise ValueError('Pinned source generation is missing')
            authorize(scope,connection.execute('SELECT clock_timestamp()').fetchone()[0])
            return stored.document(latest_generation=latest)


    def list_current(self, ctx: TenantContext, scope: PlanScope, environment_id: str, *,
                     after: str | None = None, limit: int = 50, authorize: Callable) -> dict:
        """Bounded live listing: one latest revision per application, never history.

        One SQL statement observes drafts and inventory currency in one snapshot.
        Pages are independent live reads, not a frozen cross-page export. Re-load
        the chosen draft and retain its optimistic revision before saving edits.
        The ASCII group ID is a position only; it grants no tenant or scope access.
        """
        if (type(limit) is not int or not 1 <= limit <= 100
                or after is not None and not _id(after)):
            raise ValueError('A bounded page and exact application cursor are required')
        DiscoveryRepository._require_scope(ctx, scope, environment_id)
        args = DiscoveryRepository._scope_args(ctx, scope, environment_id)
        with self._session(ctx, scope, environment_id, authorize) as connection:
            rows = connection.execute(
                'WITH source AS (SELECT max(generation) AS latest_generation FROM '
                'hosting_controlplane.discovery_generations WHERE '+_SCOPE_SQL+'), '
                'drafts AS (SELECT DISTINCT ON (application_group_id COLLATE "C") '+_COLUMNS+
                ' FROM hosting_controlplane.application_draft_revisions WHERE '+_SCOPE_SQL+
                ' AND application_group_id COLLATE "C" > %s '
                'ORDER BY application_group_id COLLATE "C", revision DESC LIMIT %s) '
                'SELECT source.latest_generation, drafts.* FROM source LEFT JOIN drafts ON true '
                'ORDER BY drafts.application_group_id COLLATE "C"',
                (*args, *args, after or '', limit+1)).fetchall()
            if not rows or len(rows) > limit+1:
                raise ValueError('Invalid bounded application listing')
            latest = rows[0][0]
            if latest is not None and (type(latest) is not int or not 1 <= latest <= _MAX):
                raise ValueError('Invalid source generation')
            stored = []
            for row in rows:
                if row[0] != latest:
                    raise ValueError('Inconsistent listing source generation')
                if row[1] is None:  # Empty LEFT JOIN, not a missing draft payload.
                    if len(rows) != 1 or any(value is not None for value in row[1:]):
                        raise ValueError('Invalid empty application listing')
                    continue
                item = self._row(environment_id, scope, row[1:])
                if latest is None or latest < item.generation:
                    raise ValueError('Pinned application source generation is missing')
                if item.application_group_id <= (stored[-1].application_group_id if stored else after or ''):
                    raise ValueError('Application listing did not advance')
                stored.append(item)
            items = [item.summary(latest_generation=latest) for item in stored[:limit]]
            authorize(scope, connection.execute('SELECT clock_timestamp()').fetchone()[0])
            return {'format': 'hosting-application-draft-list/1',
                    'environmentId': environment_id, 'scope': vars(scope),
                    'latestGeneration': latest, 'consistency': 'LIVE_PAGE',
                    'items': items,
                    'nextAfter': items[-1]['applicationGroupId'] if len(stored) > limit else None,
                    'executionAuthorized': False}
