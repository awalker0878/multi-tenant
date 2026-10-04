"""Authenticated independent commissioning of a cross-tenant scheduling pool.

The commissioning database identity owns only this enrollment. Tenant admission
gets a boolean through the existing wave scheduler; it cannot enroll a pool,
read another tenant's rows or obtain native permission through this owner.
"""
from __future__ import annotations

import base64
from datetime import datetime
import json

from provisioner.controlplane.evidence.gate import EvidenceMutationGate
from provisioner.controlplane.evidence.repository import EvidenceRepository, _canonical
from provisioner.controlplane.evidence.vault import VaultTransitVerifier
from provisioner.controlplane.persistence import TenantContext
from provisioner.controlplane.jobs.repository import _digest

from .enterprise_wave import EnterpriseWavePool
from .wave_schedule import _require, _identifier

FORMAT = 'hosting-enterprise-wave-budget-approval/1'


def native_budget_record(pool):
    value = pool.to_record()
    value.pop('nativeBudgetEvidenceDigest')
    value['format'] = 'hosting-enterprise-native-budget-observation/1'
    return value


def approval_payload(pool, context, key_id):
    _require(isinstance(pool, EnterpriseWavePool) and isinstance(context, TenantContext),
             'Exact independently observed native pool and tenant required')
    _identifier(key_id)
    _require((context.organization_id, context.tenant_id) in {d.key[:2] for d in pool.domains},
             'The approving tenant is outside the native pool')
    return {'format': FORMAT, 'organizationId': context.organization_id,
            'tenantId': context.tenant_id, 'poolId': pool.pool_id, 'poolDigest': pool.digest,
            'nativeBudgetEvidenceDigest': pool.native_budget_evidence_digest,
            'observedAt': pool.observed_at.isoformat(), 'expiresAt': pool.expires_at.isoformat(),
            'keyId': key_id}


class EnterprisePoolCommissioner:
    def __init__(self, connect, *, evidence: EvidenceRepository, custody: EvidenceMutationGate,
                 verifier: VaultTransitVerifier, budget_keys: dict[tuple[str, str], str]):
        _require(callable(connect) and isinstance(evidence, EvidenceRepository)
                 and isinstance(custody, EvidenceMutationGate)
                 and isinstance(verifier, VaultTransitVerifier) and type(budget_keys) is dict
                 and 2 <= len(budget_keys) <= 256,
                 'Actual independent database, retained custody and Vault budget verifier required')
        for scope, key in budget_keys.items():
            _require(type(scope) is tuple and len(scope) == 2, 'Exact budget signer scope required')
            for value in (*scope, key):
                _identifier(value)
        self._connect, self._evidence, self._custody, self._verifier = connect, evidence, custody, verifier
        self._keys = dict(budget_keys)

    def enroll(self, pool: EnterpriseWavePool, *, actor: str):
        _require(isinstance(pool, EnterpriseWavePool), 'Immutable native budget pool required')
        _identifier(actor)
        # Authenticate each tenant's exact current approval before any global
        # enrollment. One tenant or a retained success flag cannot approve all.
        for org, tenant in sorted({d.key[:2] for d in pool.domains}):
            context = TenantContext(org, tenant)
            key = self._keys.get((org, tenant))
            _require(key is not None, 'No independently enrolled scoped budget signer')
            self._custody.require(context)
            budget = self._evidence.get(context, 'native-budget-'+pool.native_budget_evidence_digest)
            _require(budget is not None and budget[0].evidence_kind == 'OBSERVATION'
                     and budget[0].subject_id == pool.pool_id
                     and budget[0].blob_digest == pool.native_budget_evidence_digest
                     and budget[1] == native_budget_record(pool)
                     and _digest(budget[1]) == pool.native_budget_evidence_digest,
                     'The actual original aggregate native budget observation is unavailable')
            original = self._evidence.get(context, 'enterprise-pool-'+pool.digest)
            _require(original is not None, 'Retained independent native budget approval unavailable')
            entry, envelope = original
            expected = approval_payload(pool, context, key)
            _require(entry.evidence_kind == 'VERIFICATION_RESULT' and entry.subject_id == pool.pool_id
                     and type(envelope) is dict and set(envelope) == {'payload', 'signature'}
                     and envelope['payload'] == expected and type(envelope['signature']) is str,
                     'Retained budget approval belongs to another pool or tenant')
            try:
                signature = base64.b64decode(envelope['signature'], validate=True)
                self._verifier.verify(key, _canonical(expected), signature)
            except Exception:
                _require(False, 'Independent native budget signature is unavailable or revoked')
        with self._connect() as connection, connection.cursor() as cursor:
            _require(not connection.autocommit, 'Transactional independent commissioning identity required')
            cursor.execute('SELECT r.rolsuper,r.rolbypassrls,current_user=pg_get_userbyid(c.relowner) '
                'FROM pg_roles r CROSS JOIN pg_class c WHERE r.rolname=current_user '
                "AND c.oid='hosting_controlplane.enterprise_wave_pools'::regclass")
            _require(cursor.fetchone() == (False, False, True),
                     'Only the independent non-bypass pool commissioning identity may enroll')
            cursor.execute('SELECT clock_timestamp()')
            now: datetime = cursor.fetchone()[0]
            _require(pool.observed_at <= now < pool.expires_at,
                     'Independent native pool observation or approval has expired')
            cursor.execute('SELECT document_digest,document_json FROM '
                'hosting_controlplane.enterprise_wave_pools WHERE pool_id=%s FOR SHARE', (pool.pool_id,))
            previous = cursor.fetchone()
            if previous is not None:
                _require(previous[0] == pool.digest and previous[1] == pool.to_record(),
                         'The original pool enrollment is immutable')
                return pool.digest
            cursor.execute('INSERT INTO hosting_controlplane.enterprise_wave_pools '
                '(pool_id,document_digest,document_json,enrolled_by) VALUES(%s,%s,%s::jsonb,%s)',
                (pool.pool_id, pool.digest, json.dumps(pool.to_record(), sort_keys=True,
                 separators=(',', ':'), allow_nan=False), actor))
        return pool.digest
