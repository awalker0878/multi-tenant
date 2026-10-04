"""Current, independently enrolled Vault proofs retained by the evidence owner.

The proof-verifier database identity is separate from the importer/runtime. A
database receipt never replaces the retained signed envelope: each use verifies
its original Object Lock evidence and current Vault key enrollment again.
"""
from __future__ import annotations

import base64
from dataclasses import dataclass
from datetime import timedelta

from provisioner.controlplane.authority.service import AuthorityDenied
from provisioner.controlplane.evidence.gate import EvidenceMutationGate
from provisioner.controlplane.evidence.repository import _canonical
from provisioner.controlplane.evidence.vault import VaultTransitVerifier
from provisioner.controlplane.jobs.repository import _json, _tenant
from provisioner.controlplane.persistence import TenantContext
from provisioner.execution import readback_core as c
from provisioner.execution.run_files import digest, encoded, require

PURPOSES = frozenset({'IMPORT', 'CUSTODY', 'NATIVE', 'EXCLUSION', 'OWNER', 'SECURITY'})
PROOF_FORMAT = 'hosting-retained-conversion-proof/1'
MAX_FRESHNESS = timedelta(minutes=5)


def scope_digest(scope: dict) -> str:
    from .rehearsal import SCOPE_FIELDS
    c.exact_keys(scope, SCOPE_FIELDS)
    return digest(encoded(scope))


def proof_header(envelope: dict, *, now):
    c.exact_keys(envelope, {'payload', 'keyId', 'signature', 'statement'})
    payload = envelope['payload']
    c.exact_keys(payload, {'format', 'purpose', 'batchId', 'manifestDigest',
                          'scopeDigest', 'statementDigest', 'subjectId',
                          'observedAt', 'freshUntil'})
    require(payload['format'] == PROOF_FORMAT and payload['purpose'] in PURPOSES,
            'Exact supported retained conversion proof required')
    for key in ('batchId', 'subjectId'):
        c.identifier(payload[key])
    c.identifier(envelope['keyId'])
    for key in ('manifestDigest', 'scopeDigest', 'statementDigest'):
        require(isinstance(payload[key], str) and c.HEX.fullmatch(payload[key]),
                'Exact conversion proof digest required')
    observed, fresh = c.timestamp(payload['observedAt']), c.timestamp(payload['freshUntil'])
    require(observed <= now < fresh and timedelta(0) < fresh-observed <= MAX_FRESHNESS,
            'Conversion proof is future, stale or exceeds the five-minute intake window')
    require(isinstance(envelope['statement'], dict) and
            digest(encoded(envelope['statement'])) == payload['statementDigest'],
            'Conversion proof statement bytes differ')
    try:
        signature = base64.b64decode(envelope['signature'], validate=True)
    except (TypeError, ValueError) as exc:
        raise AuthorityDenied('Conversion proof signature encoding is invalid') from exc
    require(signature and len(signature) <= 2048, 'Bounded conversion proof signature required')
    return payload, signature


@dataclass(frozen=True)
class VerifiedConversionProof:
    event_key: str
    artifact_digest: str
    key_id: str
    purpose: str
    subject_id: str
    payload: dict
    statement: dict


class ConversionProofs:
    """Concrete Vault/evidence intake; no caller-supplied accepted booleans."""

    def __init__(self, connect, *, evidence_gate: EvidenceMutationGate,
                 verifier: VaultTransitVerifier):
        if (not callable(connect) or not isinstance(evidence_gate, EvidenceMutationGate)
                or not isinstance(verifier, VaultTransitVerifier)):
            raise TypeError('Separate proof-verifier DB, existing evidence and Vault owners required')
        if len(set(verifier._trusted.values())) != len(verifier._trusted):
            raise ValueError('Conversion signing identities cannot alias the same Vault Transit key')
        self._connect = connect
        self.evidence = evidence_gate
        self.verifier = verifier

    def verify(self, cursor, context: TenantContext, scope: dict, *, event_key: str,
               batch_id: str, manifest_digest: str, purpose: str,
               enrolled_receipt: bool = True) -> VerifiedConversionProof:
        c.identifier(event_key)
        self.evidence.require(context)
        retained = self.evidence.evidence.get(context, event_key)
        require(retained is not None, 'Independently retained conversion proof is missing')
        entry, envelope = retained
        cursor.execute('SELECT clock_timestamp()')
        now = cursor.fetchone()[0]
        payload, signature = proof_header(envelope, now=now)
        require((entry.evidence_kind, entry.subject_id) == ('RECOVERY_DECISION', batch_id),
                'Conversion proof belongs to another evidence kind or batch')
        require((payload['purpose'], payload['batchId'], payload['manifestDigest'],
                 payload['scopeDigest']) == (purpose, batch_id, manifest_digest, scope_digest(scope)),
                'Conversion proof covers another exact source batch or scope')
        cursor.execute(
            'SELECT subject_id, valid_from, valid_until FROM '
            'hosting_controlplane.retained_conversion_keys k WHERE organization_id=%s '
            'AND tenant_id=%s AND security_domain_id=%s AND workload_id=%s '
            'AND scope_digest=%s AND key_id=%s AND purpose=%s '
            'AND NOT EXISTS (SELECT 1 FROM hosting_controlplane.retained_conversion_key_revocations r '
            'WHERE r.organization_id=k.organization_id AND r.tenant_id=k.tenant_id '
            'AND r.key_id=k.key_id AND r.purpose=k.purpose AND r.scope_digest=k.scope_digest) '
            '',
            (context.organization_id, context.tenant_id, scope['securityDomainId'],
             scope['workloadId'], scope_digest(scope), envelope['keyId'], purpose))
        key = cursor.fetchone()
        require(key is not None and key[0] == payload['subjectId'] and key[1] <= now < key[2],
                'Conversion signer is unenrolled, revoked, expired or outside this exact scope')
        self.verifier.verify(envelope['keyId'], _canonical(payload), signature)
        if enrolled_receipt:
            cursor.execute(
                'SELECT artifact_digest, envelope FROM hosting_controlplane.retained_conversion_proofs '
                'WHERE organization_id=%s AND tenant_id=%s AND event_key=%s',
                (context.organization_id, context.tenant_id, event_key))
            receipt = cursor.fetchone()
            require(receipt is not None and receipt[0] == entry.blob_digest and
                    _json(receipt[1]) == envelope,
                    'Independently verified conversion receipt is absent or changed')
        self.evidence.require(context)
        return VerifiedConversionProof(event_key, entry.blob_digest, envelope['keyId'],
            purpose, payload['subjectId'], payload, envelope['statement'])

    def intake(self, context: TenantContext, scope: dict, *, event_key: str,
               batch_id: str, manifest_digest: str, purpose: str) -> VerifiedConversionProof:
        """Run using the separately granted proof-verifier role, never runtime."""
        with self._connect() as connection, connection.cursor() as cursor:
            _tenant(cursor, context)
            proof = self.verify(cursor, context, scope, event_key=event_key,
                batch_id=batch_id, manifest_digest=manifest_digest, purpose=purpose,
                enrolled_receipt=False)
            retained = self.evidence.evidence.get(context, event_key)
            require(retained is not None and retained[0].blob_digest == proof.artifact_digest,
                    'Retained proof changed during independent intake')
            cursor.execute(
                'INSERT INTO hosting_controlplane.retained_conversion_proofs '
                '(organization_id,tenant_id,event_key,artifact_digest,scope_digest,batch_id,'
                'manifest_digest,key_id,purpose,subject_id,observed_at,fresh_until,envelope) '
                'VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb) ON CONFLICT DO NOTHING',
                (context.organization_id, context.tenant_id, event_key, proof.artifact_digest,
                 scope_digest(scope), batch_id, manifest_digest, proof.key_id, proof.purpose,
                 proof.subject_id, proof.payload['observedAt'], proof.payload['freshUntil'],
                 _canonical(retained[1]).decode()))
            cursor.execute(
                'SELECT artifact_digest,envelope FROM hosting_controlplane.retained_conversion_proofs '
                'WHERE organization_id=%s AND tenant_id=%s AND event_key=%s',
                (context.organization_id, context.tenant_id, event_key))
            actual = cursor.fetchone()
            require(actual is not None and actual[0] == proof.artifact_digest and
                    _json(actual[1]) == retained[1], 'Conversion proof receipt identity conflicts')
            return proof


def require_independent(proofs: list[VerifiedConversionProof]) -> None:
    require(len({proof.key_id for proof in proofs}) == len(proofs) and
            len({proof.subject_id for proof in proofs}) == len(proofs),
            'Custody, native, exclusion, import, owner and security proof owners must be independent')
