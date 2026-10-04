"""Final-code pilot acceptance and signed release preparation.

Uses independently verified pilot acceptance and current native mobility
campaigns. It prepares artifacts for the receiving/release owner; no remote
publication, automatic pilot acceptance or production grant occurs here.
"""
from __future__ import annotations

import base64
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import ssl

from provisioner.qualification import mobility, target_selection
from provisioner.qualification.intake import FinalEvidenceIntake

PILOT_SCENARIOS = ('GUIDED_DISCOVERY_AND_APPLICATION_REVIEW',
                   'GUIDED_PROVISIONING_AND_MIGRATION',
                   'INTERRUPTION_CONTAINMENT_AND_RECOVERY',
                   'ON_CALL_ALERT_AND_ACKNOWLEDGEMENT',
                   'OBSERVATION_ONLY_RESTORE_AND_UPGRADE',
                   'RECEIVING_TEAM_HANDOVER_AND_FIRST_WAVE')


def _canonical(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=False, allow_nan=False).encode('utf-8')


def pilot_run_sheet(spec: mobility.MobilityCampaign) -> dict:
    return {'format': 'hosting-final-code-pilot-run-sheet/1',
            'codeRevision': spec.code_revision,
            'installedArtifactSha256': spec.installed_artifact_sha256,
            'routeId': spec.route_id,
            'scenarios': [{'id': scenario, 'result': 'NOT_RUN', 'evidenceRef': None}
                          for scenario in PILOT_SCENARIOS],
            'requiredExternalOwners': ['actual-sysadmin', 'production-change-authority',
                                      'receiving-service-owner', 'independent-evidence-custodian'],
            'pilotAccepted': False, 'mutationAuthorized': False}


def _verify_pilot(envelope: dict, verifier, *, revision: str, artifact_digest: str,
                  matrix_digest: str, as_of: datetime) -> dict:
    if not isinstance(envelope, dict) or set(envelope) != {'payload', 'keyId', 'signature'}:
        raise ValueError('Independently signed final-code pilot acceptance required')
    payload = envelope['payload']
    if not isinstance(payload, dict) or set(payload) != {
            'format', 'codeRevision', 'installedArtifactSha256', 'supportMatrixSha256',
            'receivingTeamRef', 'changeAuthorityRef', 'acceptanceRef', 'acceptedAt',
            'expiresAt', 'scenarios'} or payload['format'] != 'hosting-pilot-acceptance/1':
        raise ValueError('Strict pilot acceptance artifact required')
    verifier.verify(envelope['keyId'], _canonical(payload),
                    base64.b64decode(envelope['signature'], validate=True))
    if (payload['codeRevision'], payload['installedArtifactSha256'], payload['supportMatrixSha256']) != (
            revision, artifact_digest, matrix_digest):
        raise ValueError('Pilot acceptance predates the final installed/support state')
    for key in ('receivingTeamRef', 'changeAuthorityRef', 'acceptanceRef'):
        target_selection.opaque_ref(payload[key], key)
    accepted = target_selection.instant(payload['acceptedAt'], 'acceptedAt')
    expires = target_selection.instant(payload['expiresAt'], 'expiresAt')
    if accepted > as_of or not accepted < expires or as_of >= expires:
        raise ValueError('Pilot acceptance is not current')
    scenarios = payload['scenarios']
    if not isinstance(scenarios, list) or len(scenarios) != len(PILOT_SCENARIOS):
        raise ValueError('Every actual pilot scenario needs receiving-team acceptance')
    seen = set()
    for scenario in scenarios:
        if (not isinstance(scenario, dict) or set(scenario) != {'id', 'result', 'evidenceRef', 'artifactSha256'}
                or scenario['id'] not in PILOT_SCENARIOS or scenario['id'] in seen
                or scenario['result'] != 'ACCEPTED'
                or not mobility._SHA.fullmatch(scenario['artifactSha256'])):
            raise ValueError('Pilot scenario remains unaccepted or lacks exact retained evidence')
        target_selection.opaque_ref(scenario['evidenceRef'], 'pilot scenario evidence')
        seen.add(scenario['id'])
    return payload


def prepare(archive: Path, specifications: list[mobility.MobilityCampaign], *,
            qualification_index: dict, provenance_index: dict, campaign_index: dict,
            selection_index: dict, pilot_envelope: dict, pilot_verifier, release_signer,
            evidence_intake: FinalEvidenceIntake, destination: Path,
            as_of: datetime | None = None) -> dict:
    """Create a signed final-revision release/support artifact after real pilot evidence."""
    as_of = as_of or datetime.now(timezone.utc)
    if (as_of.tzinfo is None or not specifications or len(specifications) > 128
            or type(evidence_intake) is not FinalEvidenceIntake):
        raise ValueError('Finite final-code route set and current review instant required')
    digest = hashlib.sha256()
    with Path(archive).open('rb') as source:
        for chunk in iter(lambda: source.read(1048576), b''):
            digest.update(chunk)
    artifact_digest = digest.hexdigest()
    if any(spec.installed_artifact_sha256 != artifact_digest for spec in specifications):
        raise ValueError('Release bytes differ from qualified installed artifact')
    assessments = [mobility.assess(spec, qualification_index=qualification_index,
        provenance_index=provenance_index, campaign_index=campaign_index,
        selection_index=selection_index, as_of=as_of) for spec in specifications]
    if any(item['status'] != 'CURRENT_NATIVE_EVIDENCE_SELECTED' for item in assessments):
        raise ValueError('Every advertised route must have current final-code native evidence')
    for spec, assessment in zip(specifications, assessments):
        evidence_intake.require_campaign(spec, assessment, campaign_index, qualification_index, as_of=as_of)
    matrix = mobility.unsupported_matrix(assessments)
    matrix_digest = hashlib.sha256(_canonical(matrix)).hexdigest()
    acceptance = _verify_pilot(pilot_envelope, pilot_verifier,
        revision=matrix['codeRevision'], artifact_digest=artifact_digest,
        matrix_digest=matrix_digest, as_of=as_of)
    evidence_intake.require_pilot(acceptance, as_of=as_of)
    if release_signer.key_id == pilot_envelope['keyId']:
        raise ValueError('Receiving pilot acceptance and release signing require different owner identities')
    if (release_signer.key_id in evidence_intake.key_ids or pilot_envelope['keyId'] in evidence_intake.key_ids):
        raise ValueError('Independent observation, receiving acceptance and release need different owner keys')
    manifest = {'format': 'hosting-supported-release-manifest/1',
                'codeRevision': matrix['codeRevision'], 'installedArtifactSha256': artifact_digest,
                'supportMatrixSha256': matrix_digest,
                'pilotAcceptanceSha256': hashlib.sha256(_canonical(pilot_envelope)).hexdigest(),
                'pilotAcceptanceRef': acceptance['acceptanceRef'],
                'preparedAt': as_of.isoformat(), 'advertisedRoutes': [spec.route_id for spec in specifications],
                'unsupportedRowsRetained': True, 'productionAuthorityIssued': False,
                'instructionsRef': 'docs/operations/control-application/2-campaign-pilot-and-release.md'}
    signature = release_signer.sign(_canonical(manifest))
    signed = {'payload': manifest, 'keyId': release_signer.key_id,
              'signature': base64.b64encode(signature).decode('ascii')}
    destination = Path(destination)
    destination.mkdir(parents=True, mode=0o700, exist_ok=False)
    for filename, value in (('support-matrix.json', matrix), ('release-manifest.json', signed),
                            ('pilot-acceptance.json', pilot_envelope)):
        path = destination / filename
        with path.open('xb') as output:
            path.chmod(0o600)
            output.write(_canonical(value) + b'\n')
    return {'status': 'SIGNED_RELEASE_PREPARED_FOR_OWNER_PUBLICATION',
            'codeRevision': matrix['codeRevision'], 'installedArtifactSha256': artifact_digest,
            'supportMatrixSha256': matrix_digest, 'remotePublicationAttempted': False,
            'productionAuthorityIssued': False}


def verify_artifact(archive: Path, signed_manifest: dict, support_matrix: dict,
                    pilot_envelope: dict, *, release_verifier, pilot_verifier) -> dict:
    """Verify offline release bytes/custody before installation, granting no action."""
    if (not isinstance(signed_manifest, dict) or set(signed_manifest) != {'payload', 'keyId', 'signature'}
            or not isinstance(signed_manifest['payload'], dict)):
        raise ValueError('Strict signed release artifact required')
    manifest = signed_manifest['payload']
    release_verifier.verify(signed_manifest['keyId'], _canonical(manifest),
                           base64.b64decode(signed_manifest['signature'], validate=True))
    if (manifest.get('format') != 'hosting-supported-release-manifest/1'
            or manifest.get('productionAuthorityIssued') is not False
            or support_matrix.get('format') != 'hosting-mobility-support-matrix/1'
            or support_matrix.get('productionAuthorityIssued') is not False):
        raise ValueError('Release artifact cannot contain production authority')
    digest = hashlib.sha256()
    with Path(archive).open('rb') as source:
        for chunk in iter(lambda: source.read(1048576), b''):
            digest.update(chunk)
    if (digest.hexdigest() != manifest['installedArtifactSha256']
            or hashlib.sha256(_canonical(support_matrix)).hexdigest() != manifest['supportMatrixSha256']
            or hashlib.sha256(_canonical(pilot_envelope)).hexdigest() != manifest['pilotAcceptanceSha256']
            or support_matrix.get('codeRevision') != manifest['codeRevision']
            or support_matrix.get('installedArtifactSha256') != manifest['installedArtifactSha256']):
        raise ValueError('Installed bytes/support/pilot evidence differ from signed final release')
    _verify_pilot(pilot_envelope, pilot_verifier, revision=manifest['codeRevision'],
                  artifact_digest=manifest['installedArtifactSha256'],
                  matrix_digest=manifest['supportMatrixSha256'],
                  as_of=target_selection.instant(manifest['preparedAt'], 'preparedAt'))
    if signed_manifest['keyId'] == pilot_envelope['keyId']:
        raise ValueError('Receiving pilot and release custody must remain separate')
    return {'status': 'SIGNED_ARTIFACT_CUSTODY_VERIFIED', 'codeRevision': manifest['codeRevision'],
            'mutationAuthorized': False, 'currentQualificationRecheckRequired': True}


def _vault_owners(*, signing: bool):
    """Site-configured dedicated release/pilot custody, never checkpoint keys."""
    from provisioner.controlplane.evidence.runtime import (
        EvidenceRuntimeConfig, _private_file,
    )
    from provisioner.controlplane.evidence.vault import (
        VaultTransitClient, VaultTransitSigner, VaultTransitVerifier,
    )
    config = EvidenceRuntimeConfig.from_environment()
    name = re.compile(r'^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$')
    def read_trust(variable):
        def pairs(items):
            result = {}
            for key, value in items:
                if key in result:
                    raise ValueError('Duplicate release/pilot custody key')
                result[key] = value
            return result
        trust = json.loads(os.environ[variable], object_pairs_hook=pairs)
        if (not isinstance(trust, dict) or not trust or len(trust) > 32
                or any(not isinstance(key, str) or not name.fullmatch(key)
                       or not isinstance(pair, list) or len(pair) != 2
                       or not all(isinstance(item, str) and name.fullmatch(item) for item in pair)
                       for key, pair in trust.items())
                or set(trust) & set(config.trusted_keys)
                or {tuple(pair) for pair in trust.values()} & set(config.trusted_keys.values())):
            raise ValueError('Independent release/pilot key trust is required')
        return trust
    release_trust = read_trust('HOSTING_RELEASE_VAULT_TRUST_JSON')
    pilot_trust = read_trust('HOSTING_PILOT_ACCEPTANCE_VAULT_TRUST_JSON')
    if (set(release_trust) & set(pilot_trust)
            or {tuple(pair) for pair in release_trust.values()} &
               {tuple(pair) for pair in pilot_trust.values()}):
        raise ValueError('Pilot acceptance and release signing require different owner keys')
    tls = ssl.create_default_context(cafile=str(config.vault_ca))
    tls.minimum_version = ssl.TLSVersion.TLSv1_2
    client = VaultTransitClient(config.vault_url,
        lambda: _private_file(Path(os.environ['HOSTING_RELEASE_VERIFY_TOKEN_FILE'])), tls_context=tls)
    pilot_verifier = VaultTransitVerifier(client, {key: tuple(pair) for key, pair in pilot_trust.items()})
    release_verifier = VaultTransitVerifier(client, {key: tuple(pair) for key, pair in release_trust.items()})
    if not signing:
        return pilot_verifier, release_verifier, None
    key_id = os.environ['HOSTING_RELEASE_KEY_ID']
    if key_id not in release_trust:
        raise ValueError('Release signing key is outside current release-owner trust')
    mount, key = release_trust[key_id]
    signer = VaultTransitSigner(VaultTransitClient(config.vault_url,
        lambda: _private_file(Path(os.environ['HOSTING_RELEASE_SIGN_TOKEN_FILE'])), tls_context=tls),
        key_id=key_id, mount=mount, key=key)
    return pilot_verifier, release_verifier, signer


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('pilot-run-sheet', 'prepare', 'verify-artifact'))
    parser.add_argument('--specification', type=Path, action='append')
    parser.add_argument('--archive', type=Path)
    parser.add_argument('--directory', type=Path)
    parser.add_argument('--pilot-acceptance', type=Path)
    parser.add_argument('--qualification-index', type=Path)
    parser.add_argument('--provenance-index', type=Path)
    parser.add_argument('--campaign-index', type=Path)
    parser.add_argument('--selection-index', type=Path)
    args = parser.parse_args(argv)
    try:
        from provisioner.qualification import native, campaign, provenance
        from provisioner.qualification.action_gate import _protected_index
        if args.mode == 'pilot-run-sheet':
            if not args.specification or len(args.specification) != 1:
                raise ValueError('One exact final-code specification is required')
            result = pilot_run_sheet(mobility.from_document(_protected_index(args.specification[0])))
        elif args.mode == 'verify-artifact':
            if args.directory is None or args.archive is None:
                raise ValueError('Exact archived runtime and signed release directory required')
            pilot_verifier, verifier, _ = _vault_owners(signing=False)
            result = verify_artifact(args.archive,
                _protected_index(args.directory / 'release-manifest.json'),
                _protected_index(args.directory / 'support-matrix.json'),
                _protected_index(args.directory / 'pilot-acceptance.json'), release_verifier=verifier,
                pilot_verifier=pilot_verifier)
        else:
            if (not args.specification or len(args.specification) > 128 or args.archive is None
                    or args.directory is None or args.pilot_acceptance is None):
                raise ValueError('Final route specifications, runtime bytes and original pilot acceptance required')
            verifier, _, signer = _vault_owners(signing=True)
            from provisioner.qualification.intake import build_final_intake
            result = prepare(args.archive,
                [mobility.from_document(_protected_index(path)) for path in args.specification],
                qualification_index=_protected_index(args.qualification_index or native.INDEX),
                provenance_index=_protected_index(args.provenance_index or provenance.INDEX),
                campaign_index=_protected_index(args.campaign_index or campaign.INDEX),
                selection_index=_protected_index(args.selection_index or target_selection.INDEX),
                pilot_envelope=_protected_index(args.pilot_acceptance), pilot_verifier=verifier,
                release_signer=signer, evidence_intake=build_final_intake(), destination=args.directory)
        print(json.dumps(result, sort_keys=True))
        return 0
    except Exception:
        print(json.dumps({'status': 'FINAL_CODE_PILOT_OR_RELEASE_HELD',
                          'productionAuthorityIssued': False, 'remotePublicationAttempted': False}))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
