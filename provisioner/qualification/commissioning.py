"""Read-only final-installation campaign commissioning dossier.

Uses the existing directed implementation, tuple, campaign and selection owners.
It acquires no credential, calls no native endpoint and dispatches no job. Missing
site selections remain missing; metadata never becomes original native proof.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import json
import os
from pathlib import Path

from hosting_resources import RESOURCE_ROOT
from provisioner.controlplane.operations.action_gate import MINIMUM_PREREQUISITES
from provisioner.controlplane.operations.instance import digest
from provisioner.controlplane.workflow.installed_identity import InstalledApplicationIdentity
from provisioner.qualification import campaign, mobility, native, provenance, target_selection
from provisioner.qualification.action_gate import (
    SelectedQualificationGate, _ACTION_CAPABILITIES, _protected_index, bundle_digest,
    database_method_assertions)
from provisioner.qualification.directed_mobility import IMPLEMENTATIONS, WAVE_ASSERTIONS, expansion_assertions
from provisioner.qualification.release import PILOT_SCENARIOS

_RUNBOOK = 'docs/operations/control-application/'

ACQUISITION_STAGES = (
    {'id': 'SELECT_RESTRICTED_NATIVE_TARGETS',
     'roles': ['platform owner', 'source/destination security', 'change/contact/stop authority',
               'independent native observer', 'credential/evidence custodian'],
     'inputs': ['two exact native product/API/provider/hardware/license tuples',
                'separate source/destination site/cell/native campaign scopes',
                'current contact window, permitted/prohibited operations and cleanup authority',
                'independent original installed-version provenance and observer workspace'],
     'installedCli': ['python -m provisioner.qualification.target_selection --index <protected-selection-index>',
                      'python -m provisioner.qualification.provenance --index <protected-provenance-index>'],
     'runbooks': ['docs/engineering/actual-target-selection-assurance.md',
                  'docs/engineering/version-source-provenance-and-lifecycle-assurance.md']},
    {'id': 'QUALIFY_EXACT_ACTION_AND_PROFILE',
     'roles': ['platform engineering qualification owner', 'independent observer', 'security authority'],
     'inputs': ['actual endpoint action/profile native positives and earlier healthy controls for every negative',
                'original signed observation bytes, native dossier and commissioned site/capacity envelope',
                'distinct ACTION_<kind> evidence with action_variant of the full selected artifact'],
     'installedCli': ['python -m provisioner.qualification.campaign --index <protected-campaign-index>',
                      'python -m provisioner.qualification.native --index <protected-native-index>'],
     'runbooks': [_RUNBOOK + '2-campaign-pilot-and-release.md',
                  'docs/engineering/platform-native-qualification.md']},
    {'id': 'ESTABLISH_OPERATING_AND_RESTORED_WRITER_PREREQUISITES',
     'roles': ['backup/restore custodian', 'independent evidence observer', 'separate operating handover owner'],
     'inputs': ['reviewed pg_dump/pg_restore/systemctl binary digests',
                'real isolated database, original archive/manifest and independent high-water',
                'original accepted Temporal run/history prefixes',
                'current minimum operating acceptance and independently signed original prerequisite observations',
                'actual OID/system-identifier instance report plus separate owner handover'],
     'installedCli': ['python -m provisioner.controlplane.operations.recovery backup --directory <fresh-private-archive>',
                      'python -m provisioner.controlplane.operations.drills restore --archive <original-archive> --directory <fresh-private-attempt>',
                      'python -m provisioner.controlplane.operations.drills switchover --specification <approved-exact-ha-specification> --directory <fresh-private-attempt>',
                      'python -m provisioner.controlplane.operations.instance inspect'],
     'runbooks': [_RUNBOOK + '1-operating-the-selected-slice.md',
                  _RUNBOOK + '3-controlled-ha-and-restore-drills.md']},
    {'id': 'ADMIT_AND_OBSERVE_EXACT_APPLICATION_JOB',
     'roles': ['SOURCE_OWNER', 'DESTINATION_OWNER', 'SOURCE_SECURITY', 'DESTINATION_SECURITY',
               'distinct EXECUTION_OPERATOR', 'enrolled per-command native worker', 'independent observer'],
     'inputs': ['approved exact workload/plan/selection, delivery/data/source/target descriptors',
                'actual resource reservation and native occupancy/exclusion readers',
                'current mTLS worker identity, grant, lease, credential custody and allowed method/profile',
                'exact returned job ID, original start-payload digest and acknowledged Temporal run ID'],
     'installedCli': ['python -m provisioner.controlplane.workflow.application_runtime graph --selection-digest <original-selection-digest> --job-id <original-job-id>',
                      'python -m provisioner.qualification.mobility run-sheet <protected-exact-campaign-specification>',
                      'python -m provisioner.controlplane.workflow.runtime worker'],
     'authenticatedApi': ['POST /v1/plans/{exact-plan-id}/jobs with current SSO and stable Idempotency-Key',
                          'GET /v1/jobs/{exact-returned-job-id}', 'GET /v1/jobs/{exact-returned-job-id}/events'],
     'dispatchBoundary': 'Tenant dispatch claims the oldest due job, not a campaign job ID. Commission an isolated exact campaign outbox or use a separately reviewed exact-job dispatcher. This dossier never dispatches.',
     'runbooks': ['docs/engineering/application-worker-composition.md',
                  'docs/engineering/application-migration-runtime.md', _RUNBOOK + '2-campaign-pilot-and-release.md']},
    {'id': 'INTAKE_ORIGINAL_PER_ENDPOINT_EVIDENCE',
     'roles': ['independent native observer', 'original immutable evidence custodian', 'qualification owner'],
     'inputs': ['each required actual assertion/procedure/attempt and its earlier same-endpoint positive control',
                'exact direction/method/profile/tuple/job/plan/final-installed-artifact bindings',
                'original signed envelopes plus separately retained measurements/native responses'],
     'installedCli': ['python -m provisioner.qualification.intake --specification <protected-exact-campaign-specification> --endpoint <source-or-destination> --attempt <original-attempt> --qualification-index <protected-native-index> --directory <fresh-private-review-candidate>',
                      'python -m provisioner.qualification.mobility assess <protected-exact-campaign-specification>'],
     'runbooks': [_RUNBOOK + '4-original-final-code-evidence-intake.md']},
    {'id': 'REHEARSE_RETAINED_CONVERSION_AND_RERUN_CHANGED_PATHS',
     'roles': ['conversion custodian', 'separate native/exclusion/custody observers', 'owner/security handover signers'],
     'inputs': ['original retained batches/history/native IDs and real counts/digests',
                'authentic source workflow boundary and old-writer/high-water commitments',
                'observation-only import, independent reconciliation and exact scoped epoch handover',
                'new exact installed artifact and every affected rerun after deleting old paths'],
     'installedCli': ['python -m provisioner.controlplane.conversion.runtime propose --manifest <original-manifest> --source-root <retained-originals> --output <fresh-proposal>',
                      'python -m provisioner.controlplane.conversion.runtime inspect --organization-id <exact-org> --tenant-id <exact-tenant> --batch-id <original-batch>'],
     'runbooks': ['docs/operations/retained-state-authenticated-handover.md',
                  _RUNBOOK + '3-controlled-ha-and-restore-drills.md']},
    {'id': 'ACTUAL_PILOT_AND_OWNER_SIGNED_RELEASE',
     'roles': ['actual sysadmin/receiving team', 'independent pilot observer', 'change authority', 'separate release owner'],
     'inputs': ['all actual pilot scenarios on the final artifact and exact support matrix',
                'original independently signed operator/service observations',
                'separate current receiving acceptance, release custody and actual archive bytes'],
     'installedCli': ['python -m provisioner.qualification.release pilot-run-sheet --specification <protected-exact-campaign-specification>',
                      'python -m provisioner.qualification.release prepare --archive <actual-final-runtime-archive> --specification <protected-exact-campaign-specification> --pilot-acceptance <original-pilot-envelope> --directory <fresh-private-prepared-release>'],
     'runbooks': [_RUNBOOK + '4-original-final-code-evidence-intake.md']},
)


def build_dossier(*, installed_identity: InstalledApplicationIdentity, bundle: dict,
                  specifications: list[mobility.MobilityCampaign], as_of: datetime | None = None,
                  root: Path = RESOURCE_ROOT) -> dict:
    if (type(installed_identity) is not InstalledApplicationIdentity
            or not isinstance(specifications, list) or len(specifications) > 64
            or any(type(item) is not mobility.MobilityCampaign for item in specifications)):
        raise ValueError('Concrete installed identity and bounded original campaign specifications required')
    installed_identity.require_current()
    now = as_of or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError('Aware current dossier observation instant required')
    source, artifact = installed_identity.source_commit, installed_identity.artifact_sha256
    selected = target_selection.validate(bundle['targetSelection'], as_of=now, root=root)
    dossiers = native.validate(bundle['qualification'], as_of=now, root=root,
        provenance_index=bundle['provenance'], campaign_evidence_index=bundle['campaign'],
        target_selection_index=bundle['targetSelection'])
    exact_tuples = [{'platform': item['platform'], 'productTupleId': item['product_tuple_id'],
        'productTupleSha256': digest(item['product_tuple']), 'productTuple': item['product_tuple'],
        'qualificationRecordId': item['id'], 'assuranceProfiles': item['assurance_profiles']}
        for item in dossiers['records']]
    choices = {platform: sorted({item['productTupleId'] for item in exact_tuples
                                if item['platform'] == platform}) for platform in mobility.PLATFORMS}
    assessments, campaigns, seen = [], [], set()
    for spec in specifications:
        if ((spec.code_revision, spec.installed_artifact_sha256) != (source, artifact)
                or spec.route_id in seen):
            raise ValueError('Campaign must independently bind this final installation without duplicate route rows')
        seen.add(spec.route_id)
        assessment = mobility.assess(spec, qualification_index=bundle['qualification'],
            provenance_index=bundle['provenance'], campaign_index=bundle['campaign'],
            selection_index=bundle['targetSelection'], as_of=now, root=root)
        assessments.append(assessment)
        endpoints = []
        for side, endpoint in (('source', spec.source), ('destination', spec.destination)):
            tuples = [item for item in exact_tuples if (item['platform'], item['productTupleId']) ==
                      (endpoint.platform, endpoint.product_tuple_id)]
            targets = [item for item in selected['records'] if item['selection_id'] == endpoint.selection_id]
            endpoints.append({'endpoint': side, **asdict(endpoint), 'exactTuple': tuples[0] if len(tuples) == 1 else None,
                'selectionMetadata': targets[0] if len(targets) == 1 else None,
                'originalEvidenceRequired': [{'assertionId': key, 'observationClass': value,
                    'variantRef': spec.variant_ref, 'state': 'ORIGINAL_NATIVE_OBSERVATION_REQUIRED'}
                    for key, value in spec.assertions().items()]})
        campaigns.append({'specification': asdict(spec), 'specificationSha256': spec.digest,
            'routeId': spec.route_id, 'metadataAssessment': assessment, 'endpoints': endpoints,
            'state': 'ORIGINAL_NATIVE_AND_OPERATING_ACCEPTANCE_REQUIRED'})
    matrix = mobility.unsupported_matrix(assessments)
    rows = []
    for row in matrix['routes']:
        source_platform, destination_platform, method, guest = row['routeId'].split(':')
        implementation = IMPLEMENTATIONS.get((source_platform, destination_platform, method, guest))
        rows.append({'routeId': row['routeId'], 'sourceTupleIds': choices[source_platform],
            'destinationTupleIds': choices[destination_platform],
            'implementedDriver': None if implementation is None else implementation.driver,
            'implementedOwners': [] if implementation is None else list(implementation.owners),
            'requiredAssertions': sorted({**mobility.COMMON_ASSERTIONS,
                **mobility.METHOD_ASSERTIONS[method], **expansion_assertions(method)}),
            'metadataState': row['status'], 'metadataBlockers': row.get('blockers', []),
            'state': 'COMMISSIONING_HELD', 'originalNativeProofVerified': False,
            'separateDirectedEvidenceRequired': True})
    installed_identity.require_current()
    return {'format': 'hosting-final-code-commissioning-dossier/1', 'status': 'READ_ONLY_COMMISSIONING_DOSSIER',
        'sourceCommit': source, 'installedArtifactSha256': artifact, 'observedAt': now.isoformat(),
        'qualificationBundleDigest': bundle_digest(bundle), 'exactNativeTuples': exact_tuples,
        'routeRows': rows, 'selectedCampaigns': campaigns, 'acquisitionStages': list(ACQUISITION_STAGES),
        'minimumOperatingPrerequisites': sorted(MINIMUM_PREREQUISITES),
        'actionCampaignRequirements': [{'operationKind': key, 'endpoint': value[0],
            'assertionId': 'ACTION_' + key, 'qualifiedCapabilities': sorted(value[1]),
            'variantOwner': 'provisioner.qualification.action_gate.action_variant',
            **({'databaseDriverEndpoint': 'both',
                'databaseDriverSourceAdditionalCapabilities': ['capture_export', 'snapshot_consistency']}
               if key == 'RESTORE_DATA' else {})}
            for key, value in _ACTION_CAPABILITIES.items()],
        'databaseMethodPrerequisites': {
            'driver': 'openstack-linux-application-database/1',
            'method': 'APPLICATION_NATIVE_DATABASE_SYNC', 'requiredEndpoints': ['source', 'destination'],
            'requiredAssertions': database_method_assertions(),
            'variantOwner': 'provisioner.qualification.action_gate.database_method_variant',
            'boundDescriptorField': 'applicationDatabaseSelectionDigest',
            'qualificationIssued': False, 'mutationAuthorized': False},
        'explicitWaveAssertions': dict(WAVE_ASSERTIONS), 'pilotScenarios': sorted(PILOT_SCENARIOS),
        'nativeContact': False, 'jobDispatched': False, 'activeIndexesChanged': False,
        'qualificationIssued': False, 'mutationAuthorized': False, 'productionAuthorityIssued': False}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--specification', action='append', type=Path, default=[])
    parser.add_argument('--qualification-index', type=Path, default=native.INDEX)
    parser.add_argument('--provenance-index', type=Path, default=provenance.INDEX)
    parser.add_argument('--campaign-index', type=Path, default=campaign.INDEX)
    parser.add_argument('--selection-index', type=Path, default=target_selection.INDEX)
    parser.add_argument('--capacity-index', type=Path)
    args = parser.parse_args(argv)
    try:
        identity = InstalledApplicationIdentity.from_configuration(
            Path(os.environ['HOSTING_APPLICATION_RUNTIME_CONFIG']), Path(os.environ['HOSTING_APPLICATION_SOURCE_ROOT']))
        paths = dict(qualification_path=args.qualification_index, provenance_path=args.provenance_index,
            campaign_path=args.campaign_index, target_selection_path=args.selection_index)
        if args.capacity_index is not None:
            paths['capacity_path'] = args.capacity_index
        owner = SelectedQualificationGate(**paths)
        result = build_dossier(installed_identity=identity, bundle=owner.current_bundle(),
            specifications=[mobility.from_document(_protected_index(path)) for path in args.specification])
        print(json.dumps(result, sort_keys=True, indent=2))
        return 0
    except Exception:
        print(json.dumps({'status': 'FINAL_CODE_COMMISSIONING_DOSSIER_HELD', 'nativeContact': False,
                          'jobDispatched': False, 'mutationAuthorized': False}))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
