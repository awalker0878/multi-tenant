"""Guided directional mobility campaigns and final-code support selection.

Reuses the current target-selection, exported-campaign and native-qualification
owners. A route specification is a run sheet, never a mutation grant. Evidence
for another direction, method, guest, job, selected tuple or code revision cannot
make this route available. No target is contacted by this module.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re

from hosting_resources import RESOURCE_ROOT
from provisioner.qualification import campaign, native, target_selection
from provisioner.qualification.directed_mobility import (
    campaign_implementation_blockers, expansion_assertions,
)

_SHA = re.compile(r'^[0-9a-f]{64}$')
_REVISION = re.compile(r'^[0-9a-f]{40}$')
_ID = re.compile(r'^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$')
PLATFORMS = ('vmware-nsx', 'nutanix', 'openstack')
METHODS = ('APPLICATION_REBUILD_RESTORE', 'COLD_WHOLE_VM', 'SAME_FAMILY_RELOCATION',
           'APPLICATION_NATIVE_DATABASE_SYNC', 'WARM_WHOLE_VM')
GUESTS = ('linux-ubuntu-2404', 'windows-server-2022', 'LINUX', 'WINDOWS',
          'APPLIANCE', 'GPU_PASSTHROUGH', 'ENCRYPTED_VTPM', 'SHARED_DISK')

# Each required assertion is an actual campaign procedure. A passing fixture or
# an operator Boolean cannot replace its independent retained native evidence.
COMMON_ASSERTIONS = {
    'DISCOVERY_INDEPENDENT': 'POSITIVE_CONTROL',
    'WRONG_SCOPE_REJECTED': 'NEGATIVE_CONTROL',
    'STALE_APPROVAL_REJECTED': 'NEGATIVE_CONTROL',
    'REVOKED_AUTHORITY_REJECTED': 'NEGATIVE_CONTROL',
    'RESOURCE_RESERVATION_CONFIRMED': 'CAPACITY_LOAD',
    'POLICY_PERMITTED_FLOW': 'POSITIVE_CONTROL',
    'POLICY_DENIED_FLOW': 'NEGATIVE_CONTROL',
    'GUEST_AND_SERVICE_READY': 'SERVICE_OPERATION',
    'BACKUP_ISOLATED_RESTORE': 'FAILURE_RECOVERY',
    'SOURCE_WRITER_FENCED': 'FAILURE_RECOVERY',
    'FINAL_SYNC_INTEGRITY': 'SERVICE_OPERATION',
    'MEASURED_CUTOVER': 'LIFECYCLE',
    'APPLICATION_DATA_ACCEPTED': 'SERVICE_OPERATION',
    'INTERRUPTED_EXECUTION_RECONCILED': 'FAILURE_RECOVERY',
    'PREWRITE_SOURCE_RETURN': 'FAILURE_RECOVERY',
    'POSTWRITE_COMMITTED_DATA_RECOVERY': 'FAILURE_RECOVERY',
    'SOURCE_RETENTION_AND_CLEANUP': 'LIFECYCLE',
    'CONTROL_DB_OBSERVATION_RESTORE': 'FAILURE_RECOVERY',
    'EVIDENCE_HIGH_WATER_VERIFIED': 'FAILURE_RECOVERY',
    'WORKFLOW_REPLAY_AND_UPGRADE': 'FAILURE_RECOVERY',
    'ALERT_DELIVERED_AND_ACKNOWLEDGED': 'OTHER',
    'LEAST_PRIVILEGE_AND_SANDBOX': 'NEGATIVE_CONTROL',
    'SIGNED_ARTIFACT_PROVENANCE': 'OTHER',
}
METHOD_ASSERTIONS = {
    'APPLICATION_REBUILD_RESTORE': {'DATASET_METADATA_AND_CONSISTENCY': 'SERVICE_OPERATION'},
    'COLD_WHOLE_VM': {'DISK_CHAIN_AND_BOOT_REMEDIATION': 'SERVICE_OPERATION',
                      'ISOLATED_CONVERSION_IMPORT': 'LIFECYCLE'},
    'SAME_FAMILY_RELOCATION': {'DISTINCT_ENDPOINT_TOPOLOGY_MOVE': 'LIFECYCLE'},
    'APPLICATION_NATIVE_DATABASE_SYNC': {'DATABASE_LAG_AND_DIVERGENCE': 'SERVICE_OPERATION'},
    'WARM_WHOLE_VM': {'WARM_VM_RUNNING_STATE_ACCEPTED': 'SERVICE_OPERATION'},
}


def _canonical(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=False, allow_nan=False).encode('utf-8')


@dataclass(frozen=True)
class CampaignEndpoint:
    platform: str
    product_tuple_id: str
    selection_id: str
    campaign_id: str

    def __post_init__(self):
        if self.platform not in PLATFORMS:
            raise ValueError('Implemented platform family required')
        for label in ('product_tuple_id', 'selection_id', 'campaign_id'):
            value = getattr(self, label)
            if not isinstance(value, str) or not _ID.fullmatch(value) or value == 'UNSELECTED':
                raise ValueError('Exact selected endpoint and campaign identifiers required')


@dataclass(frozen=True)
class MobilityCampaign:
    source: CampaignEndpoint
    destination: CampaignEndpoint
    method: str
    guest_profile: str
    workload_id: str
    job_id: str
    plan_digest: str
    code_revision: str
    installed_artifact_sha256: str

    def __post_init__(self):
        if (not isinstance(self.source, CampaignEndpoint) or not isinstance(self.destination, CampaignEndpoint)
                or self.method not in METHODS or self.guest_profile not in GUESTS
                or not _ID.fullmatch(self.workload_id) or not _ID.fullmatch(self.job_id)
                or not _SHA.fullmatch(self.plan_digest)
                or not _REVISION.fullmatch(self.code_revision)
                or not _SHA.fullmatch(self.installed_artifact_sha256)):
            raise ValueError('Exact directional route, job, plan and installed-code binding required')
        if (self.source.selection_id == self.destination.selection_id
                or self.source.campaign_id == self.destination.campaign_id):
            raise ValueError('Distinct source and destination campaign selections required')
        if self.method == 'SAME_FAMILY_RELOCATION' and self.source.platform != self.destination.platform:
            raise ValueError('Same-family relocation requires the same platform family')

    @property
    def digest(self) -> str:
        return hashlib.sha256(_canonical(asdict(self))).hexdigest()

    @property
    def variant_ref(self) -> str:
        return 'controlled-mobility-variant:' + self.digest

    @property
    def route_id(self) -> str:
        return f'{self.source.platform}:{self.destination.platform}:{self.method}:{self.guest_profile}'

    def assertions(self) -> dict[str, str]:
        return {**COMMON_ASSERTIONS, **METHOD_ASSERTIONS[self.method],
                **expansion_assertions(self.method)}

    def run_sheet(self) -> dict:
        return {'format': 'hosting-mobility-campaign-run-sheet/1', **asdict(self),
                'routeId': self.route_id, 'variantRef': self.variant_ref,
                'specificationSha256': self.digest,
                'assertions': [{'assertionId': key, 'observationClass': value}
                               for key, value in self.assertions().items()],
                'guidedSteps': [
                    'Select exact source/destination tuples, independent observers and contact authority.',
                    'Install the exact signed code artifact and register this variant in both campaign run sheets.',
                    'Select discovered VMware Linux application data/dependencies and owner acceptance checks.',
                    'Run wrong-scope, stale, revoked, privilege, restore and containment cases before any native write.',
                    'Admit the saved plan through the control application and inspect its immutable job binding.',
                    'Rehearse isolated provisioning/data restore with business side effects suppressed.',
                    'Interrupt an accepted operation; reconcile independent observations before resumption.',
                    'Fence every source writer, final-sync, verify data, switch traffic and measure useful service.',
                    'Rehearse prewrite rollback and postwrite recovery including committed target data.',
                    'Retain source and cleanup evidence; export independent observations for qualification review.'
                ],
                'qualificationIssued': False, 'mutationAuthorized': False,
                'nativeContact': False}


def from_document(value: dict) -> MobilityCampaign:
    if not isinstance(value, dict) or set(value) != {
            'source', 'destination', 'method', 'guest_profile', 'workload_id', 'job_id',
            'plan_digest', 'code_revision', 'installed_artifact_sha256'}:
        raise ValueError('Strict mobility campaign specification required')
    return MobilityCampaign(**{**value, 'source': CampaignEndpoint(**value['source']),
                               'destination': CampaignEndpoint(**value['destination'])})


def assess(spec: MobilityCampaign, *, qualification_index: dict, provenance_index: dict,
           campaign_index: dict, selection_index: dict, as_of: datetime | None = None,
           root: Path = RESOURCE_ROOT) -> dict:
    """Select only current native dossier/evidence for this exact final-code route."""
    as_of = as_of or datetime.now(timezone.utc)
    if not isinstance(spec, MobilityCampaign) or as_of.tzinfo is None:
        raise ValueError('Validated specification and aware review instant required')
    blocks = list(campaign_implementation_blockers(spec))
    for label, index in (('qualification', qualification_index), ('campaign', campaign_index)):
        if index.get('reviewed_source_revision') != spec.code_revision:
            blocks.append(label + ':FINAL_CODE_REVISION_MISMATCH')
    selections = target_selection.validate(selection_index, as_of=as_of, root=root)
    campaign_summary = campaign.validate(campaign_index, as_of=as_of, root=root,
                                        target_selection_index=selection_index)
    dossiers = native.validate(qualification_index, as_of=as_of, root=root,
                              provenance_index=provenance_index, campaign_evidence_index=campaign_index,
                              target_selection_index=selection_index)
    selected = {row['selection_id']: row for row in selections['records']}
    campaigns = {row['campaign_id']: row for row in campaign_summary['records']}
    raw_campaigns = {row['campaign_id']: row for row in campaign_index['records']}
    expected_assertions = spec.assertions()
    retained = []
    for direction, endpoint in (('source', spec.source), ('destination', spec.destination)):
        prefix = direction + ':'
        target = selected.get(endpoint.selection_id)
        facts = campaigns.get(endpoint.campaign_id)
        if (target is None or target['state'] != 'CURRENT_SELECTED'
                or target['platform_family'] != native.CAMPAIGN_PLATFORM[endpoint.platform]
                or target['product_tuple_id'] != endpoint.product_tuple_id):
            blocks.append(prefix + 'NO_CURRENT_EXACT_TARGET_SELECTION')
        if (facts is None or facts['state'] != 'CURRENT_EVIDENCE_COMPLETE'
                or facts['selection_id'] != endpoint.selection_id
                or facts['platform_family'] != native.CAMPAIGN_PLATFORM[endpoint.platform]
                or facts['product_tuple_id'] != endpoint.product_tuple_id):
            blocks.append(prefix + 'NO_CURRENT_EXACT_CAMPAIGN_EVIDENCE')
            continue
        if set(expected_assertions) & set(facts['not_applicable_assertions']):
            blocks.append(prefix + 'REQUIRED_MOBILITY_ASSERTION_MARKED_NOT_APPLICABLE')
        latest = {}
        for attempt in raw_campaigns[endpoint.campaign_id]['attempts']:
            current = latest.get(attempt['assertion_id'])
            if current is None or target_selection.instant(attempt['observed_at'], 'observed_at') > target_selection.instant(current['observed_at'], 'observed_at'):
                latest[attempt['assertion_id']] = attempt
        dossier_rows = [row for row in dossiers['records']
                        if row['platform'] == endpoint.platform
                        and row['product_tuple_id'] == endpoint.product_tuple_id]
        dossier_evidence = {(item['ref'], item['sha256']) for row in dossier_rows for item in row['evidence']}
        if not dossier_rows:
            blocks.append(prefix + 'NO_CURRENT_EXACT_NATIVE_DOSSIER')
        for assertion, observation_class in expected_assertions.items():
            attempt = latest.get(assertion)
            if (attempt is None or assertion not in facts['latest_passing_assertions']
                    or attempt['observation_class'] != observation_class
                    or attempt['variant_ref'] != spec.variant_ref
                    or (attempt['evidence_ref'], attempt['artifact_sha256']) not in dossier_evidence):
                blocks.append(prefix + assertion + ':MISSING_CURRENT_ROUTE_BOUND_NATIVE_EVIDENCE')
            else:
                retained.append({'endpoint': direction, 'assertionId': assertion,
                                 'evidenceRef': attempt['evidence_ref'],
                                 'artifactSha256': attempt['artifact_sha256']})
    return {'format': 'hosting-mobility-support-assessment/1', 'routeId': spec.route_id,
            'specificationSha256': spec.digest, 'codeRevision': spec.code_revision,
            'installedArtifactSha256': spec.installed_artifact_sha256,
            'status': 'CURRENT_NATIVE_EVIDENCE_SELECTED' if not blocks else 'UNSUPPORTED_HELD',
            'blockers': sorted(set(blocks)), 'retainedEvidence': retained,
            'qualificationIssued': False, 'mutationAuthorized': False,
            'nativeContact': False}


def unsupported_matrix(assessments: list[dict]) -> dict:
    """Keep every directed method/profile row, including unimplemented extensions."""
    keyed = {}
    revision = None
    artifact = None
    for item in assessments:
        if (not isinstance(item, dict) or item.get('format') != 'hosting-mobility-support-assessment/1'
                or item.get('status') not in ('CURRENT_NATIVE_EVIDENCE_SELECTED', 'UNSUPPORTED_HELD')
                or item.get('qualificationIssued') is not False or item.get('mutationAuthorized') is not False
                or not _REVISION.fullmatch(item.get('codeRevision', ''))
                or not _SHA.fullmatch(item.get('installedArtifactSha256', ''))):
            raise ValueError('Native support assessment required')
        if item['routeId'] in keyed:
            raise ValueError('Duplicate support route/profile row')
        if revision is None:
            revision, artifact = item['codeRevision'], item['installedArtifactSha256']
        elif (revision, artifact) != (item['codeRevision'], item['installedArtifactSha256']):
            raise ValueError('Support matrix must cover one final code artifact')
        keyed[item['routeId']] = item
    rows = []
    for source in PLATFORMS:
        for destination in PLATFORMS:
            methods = ('SAME_FAMILY_RELOCATION',) if source == destination else METHODS
            for method in methods:
                if source != destination and method == 'SAME_FAMILY_RELOCATION':
                    continue
                for guest in GUESTS:
                    route = f'{source}:{destination}:{method}:{guest}'
                    rows.append(keyed.pop(route, {'routeId': route, 'status': 'UNSUPPORTED_HELD',
                                                 'blockers': ['NO_SELECTED_IMPLEMENTATION_AND_NATIVE_EVIDENCE']}))
    if keyed:
        raise ValueError('Support assessment contains an undeclared route')
    return {'format': 'hosting-mobility-support-matrix/1', 'codeRevision': revision,
            'installedArtifactSha256': artifact, 'routes': rows,
            'mutationAuthorized': False, 'productionAuthorityIssued': False}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('run-sheet', 'assess'))
    parser.add_argument('specification', type=Path)
    parser.add_argument('--qualification-index', type=Path, default=native.INDEX)
    parser.add_argument('--provenance-index', type=Path)
    parser.add_argument('--campaign-index', type=Path, default=campaign.INDEX)
    parser.add_argument('--selection-index', type=Path, default=target_selection.INDEX)
    parser.add_argument('--as-of')
    args = parser.parse_args(argv)
    try:
        spec = from_document(campaign.load(args.specification))
        if args.mode == 'run-sheet':
            result = spec.run_sheet()
        else:
            from provisioner.qualification import provenance
            result = assess(spec, qualification_index=native.load(args.qualification_index),
                provenance_index=provenance.load(args.provenance_index or provenance.INDEX),
                campaign_index=campaign.load(args.campaign_index),
                selection_index=target_selection.load(args.selection_index),
                as_of=target_selection.instant(args.as_of, 'as_of') if args.as_of else None)
        print(json.dumps(result, indent=2))
        return 0 if args.mode == 'run-sheet' or result['status'] == 'CURRENT_NATIVE_EVIDENCE_SELECTED' else 2
    except Exception:
        print(json.dumps({'status': 'MOBILITY_CAMPAIGN_HELD', 'mutationAuthorized': False,
                          'nativeContact': False}))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
