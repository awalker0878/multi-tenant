"""Original independently signed native/pilot evidence intake.

Existing target selections, campaign validators and native dossiers own support
decisions. This owner verifies their exact referenced *bytes*, observer custody
and final direction/method/profile before staging or release. It cannot turn a
run sheet, local fixture, generated dossier or reverse-route proof into support.
"""
from __future__ import annotations

import argparse
import base64
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path

from provisioner.controlplane.persistence import TenantContext
from provisioner.qualification import mobility, target_selection


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=False, allow_nan=False).encode()


def sha256(value):
    return hashlib.sha256(canonical(value)).hexdigest()


class FinalEvidenceIntake:
    def __init__(self, *, evidence_gate, context: TenantContext, observer_verifier,
                 observer_key_ids: frozenset[str]):
        if (not isinstance(context, TenantContext)
                or not callable(getattr(evidence_gate, 'require', None))
                or not callable(getattr(getattr(evidence_gate, 'evidence', None), 'get', None))
                or not callable(getattr(observer_verifier, 'verify', None))
                or not isinstance(observer_key_ids, frozenset) or not observer_key_ids):
            raise ValueError('Original independent evidence custody and current observer trust required')
        self.evidence_gate, self.context = evidence_gate, context
        self.verifier, self.key_ids = observer_verifier, observer_key_ids

    def _artifact(self, reference: str, expected_digest: str, *, signed=False):
        target_selection.opaque_ref(reference, 'original evidence reference')
        if not mobility._SHA.fullmatch(expected_digest):
            raise ValueError('Exact original independent artifact digest required')
        self.evidence_gate.require(self.context)
        found = self.evidence_gate.evidence.get(self.context, reference)
        if (found is None or found[0].event_key != reference
                or found[0].evidence_kind not in ('OBSERVATION', 'NATIVE_RECEIPT', 'VERIFICATION_RESULT')
                or sha256(found[1]) != expected_digest):
            raise ValueError('Original campaign/pilot evidence bytes are unavailable or changed')
        value = found[1]
        if signed:
            if (not isinstance(value, dict) or set(value) != {'payload', 'keyId', 'signature'}
                    or value['keyId'] not in self.key_ids):
                raise ValueError('Separate enrolled independent native observer signature required')
            self.verifier.verify(value['keyId'], canonical(value['payload']),
                                 base64.b64decode(value['signature'], validate=True))
            value = value['payload']
        return value

    @staticmethod
    def _time(payload, as_of):
        observed = target_selection.instant(payload['observedAt'], 'observedAt')
        fresh = target_selection.instant(payload['freshUntil'], 'freshUntil')
        if observed > as_of or fresh <= observed or as_of >= fresh:
            raise ValueError('Independent final-code evidence is stale or future-dated')
        return observed, fresh

    def require_native_observation(self, spec: mobility.MobilityCampaign, *, endpoint: str,
                                   attempt: dict, product_tuple: dict,
                                   as_of: datetime | None = None) -> dict:
        as_of = as_of or datetime.now(timezone.utc)
        if (not isinstance(spec, mobility.MobilityCampaign) or endpoint not in ('source', 'destination')
                or not isinstance(product_tuple, dict) or not product_tuple):
            raise ValueError('Separate exact source/destination campaign specification required')
        payload = self._artifact(attempt['evidence_ref'], attempt['artifact_sha256'], signed=True)
        if not isinstance(payload, dict) or set(payload) != {
                'format', 'specificationSha256', 'routeId', 'endpoint', 'platform', 'productTupleId',
                'productTupleSha256', 'selectionId', 'campaignId', 'assertionId', 'observationClass', 'attemptId',
                'procedureRef', 'variantRef', 'codeRevision', 'installedArtifactSha256',
                'workloadId', 'jobId', 'planDigest', 'executionOrigin', 'observedAt', 'freshUntil',
                'result', 'positiveControlEvidenceRef', 'observationEvidenceRef',
                'observationArtifactSha256', 'observerRef'}:
            raise ValueError('Strict independently signed native campaign observation required')
        selected = getattr(spec, endpoint)
        bindings = {'format': 'hosting-final-native-campaign-observation/1',
            'specificationSha256': spec.digest, 'routeId': spec.route_id, 'endpoint': endpoint,
            'platform': selected.platform, 'productTupleId': selected.product_tuple_id,
            'productTupleSha256': sha256(product_tuple),
            'selectionId': selected.selection_id, 'campaignId': selected.campaign_id,
            'assertionId': attempt['assertion_id'], 'observationClass': attempt['observation_class'],
            'attemptId': attempt['attempt_id'], 'procedureRef': attempt['procedure_ref'],
            'variantRef': spec.variant_ref, 'codeRevision': spec.code_revision,
            'installedArtifactSha256': spec.installed_artifact_sha256, 'workloadId': spec.workload_id,
            'jobId': spec.job_id, 'planDigest': spec.plan_digest,
            'executionOrigin': 'COMMISSIONED_NATIVE', 'result': attempt['result']}
        if (any(payload[key] != value for key, value in bindings.items())
                or attempt['variant_ref'] != spec.variant_ref or attempt['result'] != 'PASSED'
                or spec.assertions().get(attempt['assertion_id']) != attempt['observation_class']):
            raise ValueError('Evidence belongs to another direction/method/profile/tuple/final code or failed run')
        observed, fresh = self._time(payload, as_of)
        if (observed != target_selection.instant(attempt['observed_at'], 'attempt observed_at')
                or fresh != target_selection.instant(attempt['fresh_until'], 'attempt fresh_until')):
            raise ValueError('Campaign chronology differs from original signed observation')
        target_selection.opaque_ref(payload['observerRef'], 'independent observer')
        raw = self._artifact(payload['observationEvidenceRef'], payload['observationArtifactSha256'])
        if (not isinstance(raw, dict) or raw.get('format') != 'hosting-independent-native-observation/1'
                or raw.get('specificationSha256') != spec.digest or raw.get('endpoint') != endpoint
                or raw.get('assertionId') != attempt['assertion_id']
                or raw.get('executionOrigin') != 'COMMISSIONED_NATIVE'
                or not isinstance(raw.get('observations'), dict) or not raw['observations']):
            raise ValueError('Exact original native response/observer measurements are missing')
        if attempt['observation_class'] == 'NEGATIVE_CONTROL':
            if payload['positiveControlEvidenceRef'] is None:
                raise ValueError('A native negative needs its earlier healthy positive control')
        elif payload['positiveControlEvidenceRef'] is not None:
            target_selection.opaque_ref(payload['positiveControlEvidenceRef'], 'positive control')
        self.evidence_gate.require(self.context)
        return payload

    def require_campaign(self, spec, assessment: dict, campaign_index: dict,
                         qualification_index: dict, *, as_of=None):
        as_of = as_of or datetime.now(timezone.utc)
        if (assessment.get('status') != 'CURRENT_NATIVE_EVIDENCE_SELECTED'
                or assessment.get('specificationSha256') != spec.digest):
            raise ValueError('Existing current final-code native dossier selection is required')
        records = {row['campaign_id']: row for row in campaign_index['records']}
        verified = {}
        for endpoint in ('source', 'destination'):
            selected = getattr(spec, endpoint)
            dossiers = [row for row in qualification_index['records'] if row['platform'] == selected.platform
                        and row['product_tuple_id'] == selected.product_tuple_id]
            if not dossiers or len({sha256(row['product_tuple']) for row in dossiers}) != 1:
                raise ValueError('One exact current native product tuple is required per endpoint')
            attempts = records[selected.campaign_id]['attempts']
            latest = {}
            for attempt in attempts:
                old = latest.get(attempt['assertion_id'])
                if old is None or target_selection.instant(attempt['observed_at'], 'observed_at') > target_selection.instant(old['observed_at'], 'observed_at'):
                    latest[attempt['assertion_id']] = attempt
            for assertion in spec.assertions():
                attempt = latest[assertion]
                payload = self.require_native_observation(spec, endpoint=endpoint, attempt=attempt,
                    product_tuple=dossiers[0]['product_tuple'], as_of=as_of)
                verified[(endpoint, assertion)] = (attempt, payload)
            for assertion in spec.assertions():
                attempt, payload = verified[(endpoint, assertion)]
                if attempt['observation_class'] == 'NEGATIVE_CONTROL':
                    control = next((item for item in verified.values() if
                        item[0]['attempt_id'] == attempt['positive_control_attempt_ref']
                        and item[1]['endpoint'] == endpoint), None)
                    if (control is None or control[0]['observation_class'] != 'POSITIVE_CONTROL'
                            or payload['positiveControlEvidenceRef'] != control[0]['evidence_ref']
                            or target_selection.instant(control[1]['observedAt'], 'positive observedAt') >=
                               target_selection.instant(payload['observedAt'], 'negative observedAt')):
                        raise ValueError('Negative native result lacks its exact prior healthy endpoint control')
        return {'status': 'ORIGINAL_CURRENT_NATIVE_BYTES_VERIFIED', 'specificationSha256': spec.digest,
                'observations': len(verified), 'qualificationIssued': False}

    def require_pilot(self, payload: dict, *, as_of: datetime) -> None:
        for scenario in payload['scenarios']:
            proof = self._artifact(scenario['evidenceRef'], scenario['artifactSha256'], signed=True)
            if (not isinstance(proof, dict) or set(proof) != {'format', 'scenarioId', 'codeRevision',
                    'installedArtifactSha256', 'supportMatrixSha256', 'receivingTeamRef',
                    'changeAuthorityRef', 'observedAt', 'freshUntil', 'result', 'executionOrigin',
                    'observationEvidenceRef', 'observationArtifactSha256', 'observerRef'}
                    or any(proof[key] != value for key, value in {
                        'format': 'hosting-final-pilot-scenario-observation/1', 'scenarioId': scenario['id'],
                        'codeRevision': payload['codeRevision'],
                        'installedArtifactSha256': payload['installedArtifactSha256'],
                        'supportMatrixSha256': payload['supportMatrixSha256'],
                        'receivingTeamRef': payload['receivingTeamRef'],
                        'changeAuthorityRef': payload['changeAuthorityRef'],
                        'result': 'ACCEPTED', 'executionOrigin': 'COMMISSIONED_PILOT'}.items())):
                raise ValueError('Actual independently observed final-code pilot scenario is missing')
            observed, _ = self._time(proof, as_of)
            if observed > target_selection.instant(payload['acceptedAt'], 'pilot acceptedAt'):
                raise ValueError('Pilot acceptance predates actual scenario observations')
            raw = self._artifact(proof['observationEvidenceRef'], proof['observationArtifactSha256'])
            if (not isinstance(raw, dict) or raw.get('format') != 'hosting-independent-pilot-observation/1'
                    or raw.get('scenarioId') != scenario['id']
                    or raw.get('codeRevision') != payload['codeRevision']
                    or raw.get('installedArtifactSha256') != payload['installedArtifactSha256']
                    or not isinstance(raw.get('observations'), dict) or not raw['observations']):
                raise ValueError('Original pilot operator/service observations are missing')
        self.evidence_gate.require(self.context)

    def stage_observation(self, spec, *, endpoint, attempt, product_tuple: dict, destination: Path, as_of=None):
        payload = self.require_native_observation(spec, endpoint=endpoint, attempt=attempt,
                                                 product_tuple=product_tuple, as_of=as_of)
        directory = Path(destination)
        directory.mkdir(mode=0o700, parents=True, exist_ok=False)
        report = {'format': 'hosting-native-intake-review-candidate/1',
            'specificationSha256': spec.digest, 'routeId': spec.route_id, 'endpoint': endpoint,
            'attempt': attempt, 'verifiedObservation': payload,
            'status': 'ORIGINAL_BYTES_VERIFIED_AWAITING_QUALIFICATION_OWNER_REVIEW',
            'activeIndexesChanged': False, 'qualificationIssued': False, 'mutationAuthorized': False}
        with (directory / 'review-candidate.json').open('xb') as output:
            os.chmod(directory / 'review-candidate.json', 0o600)
            output.write(canonical(report) + b'\n')
        return report


def build_final_intake(*, environment=None):
    from provisioner.controlplane.evidence.runtime import EvidenceRuntimeConfig, build_gate
    from provisioner.controlplane.operations.runtime import build_operating_verifiers
    env = os.environ if environment is None else environment
    config = EvidenceRuntimeConfig.from_environment(env)
    (observer, observer_keys), _ = build_operating_verifiers(environment=env)
    return FinalEvidenceIntake(evidence_gate=build_gate(config),
        context=TenantContext(env['HOSTING_FINAL_EVIDENCE_ORGANIZATION_ID'], env['HOSTING_FINAL_EVIDENCE_TENANT_ID']),
        observer_verifier=observer, observer_key_ids=observer_keys)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--specification', required=True, type=Path)
    parser.add_argument('--attempt', required=True, type=Path)
    parser.add_argument('--qualification-index', type=Path)
    parser.add_argument('--endpoint', required=True, choices=('source', 'destination'))
    parser.add_argument('--directory', required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        from provisioner.qualification.action_gate import _protected_index
        from provisioner.qualification import native
        spec = mobility.from_document(_protected_index(args.specification))
        index = _protected_index(args.qualification_index or native.INDEX)
        selected = getattr(spec, args.endpoint)
        dossiers = [row for row in index['records'] if row['platform'] == selected.platform
                    and row['product_tuple_id'] == selected.product_tuple_id]
        if not dossiers or len({sha256(row['product_tuple']) for row in dossiers}) != 1:
            raise ValueError('Exact review tuple custody is missing or ambiguous')
        result = build_final_intake().stage_observation(
            spec, endpoint=args.endpoint, attempt=_protected_index(args.attempt),
            product_tuple=dossiers[0]['product_tuple'], destination=args.directory)
        print(json.dumps(result, sort_keys=True))
        return 0
    except Exception:
        print(json.dumps({'status': 'INDEPENDENT_FINAL_NATIVE_EVIDENCE_INTAKE_HELD',
                          'qualificationIssued': False, 'mutationAuthorized': False}))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
