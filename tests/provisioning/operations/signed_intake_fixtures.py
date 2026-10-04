"""Ephemeral cryptographic intake fixtures; no commissioned/native evidence."""
from copy import deepcopy
from dataclasses import asdict
from datetime import timedelta
import base64
from types import SimpleNamespace

from provisioner.qualification.intake import canonical, sha256
from provisioner.qualification.target_selection import instant


class RetainedFixture:
    def __init__(self, context):
        self.context, self.evidence, self.values, self.available = context, self, {}, True

    def require(self, context):
        if context != self.context or not self.available:
            raise ValueError('Synthetic custody unavailable or wrong scope')

    def get(self, context, reference):
        self.require(context)
        value = self.values.get(reference)
        return None if value is None else (SimpleNamespace(event_key=reference,
            evidence_kind='VERIFICATION_RESULT', subject_id='synthetic-never-native'), deepcopy(value))


def signed(payload, signer):
    return {'payload': payload, 'keyId': signer.key_id,
            'signature': base64.b64encode(signer.sign(canonical(payload))).decode()}


def attach_native(spec, bundle, custody, observer):
    for endpoint, record in zip(('source', 'destination'), bundle['campaign']['records']):
        selected = getattr(spec, endpoint)
        dossier = next(q for q in bundle['qualification']['records'] if q['platform'] == selected.platform)
        control = next(a for a in record['attempts'] if a['assertion_id'] == 'DISCOVERY_INDEPENDENT')
        for attempt in record['attempts']:
            if attempt['observation_class'] == 'NEGATIVE_CONTROL':
                attempt['observed_at'] = (instant(control['observed_at'], 'control') + timedelta(seconds=1)).isoformat()
            raw_key = 'native-raw-' + sha256({'endpoint': endpoint, 'assertion': attempt['assertion_id']})
            raw = {'format': 'hosting-independent-native-observation/1', 'specificationSha256': spec.digest,
                'endpoint': endpoint, 'assertionId': attempt['assertion_id'],
                'executionOrigin': 'COMMISSIONED_NATIVE', 'observations': {'fixtureOnlyNeverNative': True}}
            custody.values[raw_key] = raw
            payload = {'format': 'hosting-final-native-campaign-observation/1',
                'specificationSha256': spec.digest, 'routeId': spec.route_id, 'endpoint': endpoint,
                'platform': selected.platform, 'productTupleId': selected.product_tuple_id,
                'productTupleSha256': sha256(dossier['product_tuple']),
                'selectionId': selected.selection_id, 'campaignId': selected.campaign_id,
                'assertionId': attempt['assertion_id'], 'observationClass': attempt['observation_class'],
                'attemptId': attempt['attempt_id'], 'procedureRef': attempt['procedure_ref'],
                'variantRef': spec.variant_ref, 'codeRevision': spec.code_revision,
                'installedArtifactSha256': spec.installed_artifact_sha256,
                'workloadId': spec.workload_id, 'jobId': spec.job_id, 'planDigest': spec.plan_digest,
                'executionOrigin': 'COMMISSIONED_NATIVE', 'observedAt': attempt['observed_at'],
                'freshUntil': attempt['fresh_until'], 'result': attempt['result'],
                'positiveControlEvidenceRef': control['evidence_ref'] if attempt['observation_class'] == 'NEGATIVE_CONTROL' else None,
                'observationEvidenceRef': raw_key, 'observationArtifactSha256': sha256(raw),
                'observerRef': 'controlled-observer:synthetic-never-native'}
            envelope = signed(payload, observer)
            custody.values[attempt['evidence_ref']] = envelope
            attempt['artifact_sha256'] = sha256(envelope)
        dossier = next(q for q in bundle['qualification']['records'] if q['platform'] == selected.platform)
        dossier['evidence'] = [{'ref': attempt['evidence_ref'], 'sha256': attempt['artifact_sha256'],
            'observed_at': attempt['observed_at'], 'expires_at': attempt['fresh_until'], 'test_set': 'CT-FIXTURE'}
            for attempt in record['attempts']]
    q = bundle['qualification']['records'][1]
    bundle['capacity']['records'][0]['qualification_binding']['qualification_record_sha256'] = sha256(q)


def attach_pilot(payload, custody, observer):
    for scenario in payload['scenarios']:
        raw_key = 'pilot-raw-' + sha256(scenario['id'])
        raw = {'format': 'hosting-independent-pilot-observation/1', 'scenarioId': scenario['id'],
               'codeRevision': payload['codeRevision'],
               'installedArtifactSha256': payload['installedArtifactSha256'],
               'observations': {'fixtureOnlyNeverPilot': True}}
        custody.values[raw_key] = raw
        proof = {'format': 'hosting-final-pilot-scenario-observation/1', 'scenarioId': scenario['id'],
            'codeRevision': payload['codeRevision'], 'installedArtifactSha256': payload['installedArtifactSha256'],
            'supportMatrixSha256': payload['supportMatrixSha256'], 'receivingTeamRef': payload['receivingTeamRef'],
            'changeAuthorityRef': payload['changeAuthorityRef'], 'observedAt': '2026-10-01T00:00:00Z',
            'freshUntil': '2026-12-31T23:59:59Z', 'result': 'ACCEPTED', 'executionOrigin': 'COMMISSIONED_PILOT',
            'observationEvidenceRef': raw_key, 'observationArtifactSha256': sha256(raw),
            'observerRef': 'controlled-observer:synthetic-never-pilot'}
        envelope = signed(proof, observer)
        custody.values[scenario['evidenceRef']] = envelope
        scenario['artifactSha256'] = sha256(envelope)


def minimum_prerequisite_artifacts(payload, observer):
    artifacts = {}
    for fact in payload['prerequisites']:
        raw_key = 'operating-raw-' + sha256({'scope': payload['scopeDigest'], 'id': fact['id']})
        raw = {'format': 'hosting-independent-selected-operating-observation/1', 'id': fact['id'],
            'scopeDigest': payload['scopeDigest'], 'sourceCommit': payload['sourceCommit'],
            'observations': {'fixtureOnlyNeverNative': True}}
        proof = {'format': 'hosting-selected-operating-prerequisite/1', 'id': fact['id'],
            'scopeDigest': payload['scopeDigest'], 'sourceCommit': payload['sourceCommit'],
            'observedAt': fact['observedAt'], 'freshUntil': fact['freshUntil'], 'observerRef': fact['observerRef'],
            'result': fact['result'], 'observationEventKey': raw_key, 'observationSha256': sha256(raw)}
        envelope = signed(proof, observer)
        fact['artifactSha256'] = sha256(envelope)
        artifacts[fact['evidenceRef']], artifacts[raw_key] = envelope, raw
    return artifacts
