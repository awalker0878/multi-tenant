"""Live exact-artifact qualification check immediately before admitted effects.

The current dossier, provenance, selected campaign and commissioned envelope
remain their existing owners. This gate adds no approval model and cannot grant
worker authority; the caller must also retain B07/B10 ownership/fencing checks.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import stat

from hosting_resources import RESOURCE_ROOT
from provisioner.allocations import capacity_evidence
from provisioner.controlplane.authority.service import AuthorityDenied
from provisioner.qualification import native, provenance, campaign, target_selection
from provisioner.qualification.directed_mobility import require_implemented_action_selection

_PLATFORM = {'vmware': 'vmware-nsx', 'vmware-nsx': 'vmware-nsx',
             'nutanix': 'nutanix', 'openstack': 'openstack'}
_ACTION_CAPABILITIES = {
    'DISCOVER_READ': ('both', {'inventory_collection', 'inventory_scope'}),
    'VM_CREATE': ('destination', {'vm_create', 'boot_volume', 'guest_linux'}),
    'VM_POWER': ('destination', {'vm_power'}),
    'DISK_ATTACH': ('destination', {'data_volumes', 'disk_order'}),
    'NETWORK_ATTACH': ('destination', {'network_domain', 'multiple_nics', 'policy_equivalence'}),
    'SNAPSHOT_CREATE': ('source', {'snapshot_consistency', 'snapshot_chain'}),
    'SNAPSHOT_EXPORT': ('source', {'capture_export'}),
    'SNAPSHOT_IMPORT': ('destination', {'image_import'}),
    'RESTORE_DATA': ('destination', {'dataset_transfer', 'data_integrity', 'backup_restore'}),
    'SOURCE_FENCE': ('source', {'source_fencing', 'source_quiesce', 'operation_reconciliation'}),
    'DESTINATION_ACTIVATE': ('destination', {'target_activation', 'guest_readiness',
                                          'backup_restore', 'operation_reconciliation',
                                          'controlplane_dr', 'evidence_retention'}),
    'DNS_CHANGE': ('destination', {'dns_registration', 'traffic_cutover'}),
    'IPAM_RESERVE': ('destination', {'capacity_reservation', 'ipam_reservation'}),
    'GUEST_CONFIG': ('destination', {'guest_linux', 'guest_customization', 'guest_identity',
                                    'guest_drivers', 'guest_readiness', 'trust_distribution'}),
    'POLICY_APPLY': ('destination', {'distributed_firewall', 'gateway_policy',
                                    'policy_equivalence', 'controlled_ingress',
                                    'controlled_egress', 'audit_logging'}),
    'QUOTA_CHANGE': ('destination', {'quota_readback', 'capacity_reservation', 'concurrency_budget'}),
}


def bundle_digest(bundle: dict) -> str:
    if not isinstance(bundle, dict) or set(bundle) != {
            'qualification', 'provenance', 'campaign', 'targetSelection', 'capacity'}:
        raise ValueError('Existing qualification/provenance/campaign/capacity indexes required')
    return hashlib.sha256(json.dumps(bundle, sort_keys=True, separators=(',', ':'),
                                    ensure_ascii=False, allow_nan=False).encode('utf-8')).hexdigest()


def action_variant(selection: dict, operation_kind: str) -> str:
    """Bind a reviewed action to directed tuples, profile, code and native scopes."""
    fields = ('sourceCommit', 'driver', 'sourceTuple', 'destinationTuple',
              'guestProfile', 'source', 'destination')
    value = {key: selection[key] for key in fields}
    value['operationKind'] = operation_kind
    return 'controlled-execution-action:' + hashlib.sha256(json.dumps(
        value, sort_keys=True, separators=(',', ':'), ensure_ascii=False,
        allow_nan=False).encode('utf-8')).hexdigest()


def _protected_index(path: Path) -> dict:
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        info = os.fstat(descriptor)
        if (not stat.S_ISREG(info.st_mode) or info.st_uid not in (0, os.geteuid())
                or info.st_mode & 0o022 or info.st_size > 4 * 1024**2):
            raise AuthorityDenied('Qualification custody index is not protected')
        raw = os.read(descriptor, 4 * 1024**2 + 1)
    finally:
        os.close(descriptor)
    def pairs(values):
        result = {}
        for key, value in values:
            if key in result:
                raise AuthorityDenied('Qualification custody index has duplicate fields')
            result[key] = value
        return result
    def constant(_):
        raise AuthorityDenied('Qualification custody index has a nonfinite number')
    return json.loads(raw, object_pairs_hook=pairs, parse_constant=constant)


class SelectedQualificationGate:
    """Re-read separately administered current indexes at each effect boundary."""

    def __init__(self, *, qualification_path: Path = native.INDEX,
                 provenance_path: Path = provenance.INDEX,
                 campaign_path: Path = campaign.INDEX,
                 target_selection_path: Path = target_selection.INDEX,
                 capacity_path: Path = capacity_evidence.INDEX,
                 root: Path = RESOURCE_ROOT):
        self.paths = {'qualification': Path(qualification_path), 'provenance': Path(provenance_path),
                      'campaign': Path(campaign_path), 'targetSelection': Path(target_selection_path),
                      'capacity': Path(capacity_path)}
        self.root = Path(root)

    def current_bundle(self) -> dict:
        return {key: _protected_index(path) for key, path in self.paths.items()}

    def require_action(self, cursor, admitted, selection: dict, operation_kind: str) -> None:
        try:
            self._require(cursor, admitted, selection, operation_kind)
        except AuthorityDenied:
            raise
        except Exception:
            raise AuthorityDenied('Exact current route/action/profile qualification is unavailable') from None

    def _require(self, cursor, admitted, selection: dict, operation_kind: str) -> None:
        if not isinstance(selection, dict) or operation_kind not in _ACTION_CAPABILITIES:
            raise AuthorityDenied('Selected installed artifact and admitted action required')
        require_implemented_action_selection(selection)
        cursor.execute("SELECT current_setting('app.organization_id',true),"
                       "current_setting('app.tenant_id',true),clock_timestamp()")
        org, tenant, now = cursor.fetchone()
        if (org, tenant) != (admitted.organization_id, admitted.tenant_id):
            raise AuthorityDenied('Qualification gate requires authenticated tenant transaction')
        for side in ('source', 'destination'):
            scope = selection[side]
            if (scope['organizationId'], scope['tenantId']) != (org, tenant):
                raise AuthorityDenied('Selected qualification crosses the admitted tenant')
        profile = selection['guestProfile']
        if not isinstance(profile, str) or not profile or len(profile) > 160:
            raise AuthorityDenied('Exact guest profile is required')
        bundle = self.current_bundle()
        if bundle_digest(bundle) != selection['qualificationDigest']:
            raise AuthorityDenied('Qualification selection changed, expired or was withdrawn')
        for key in ('qualification', 'campaign'):
            if bundle[key]['reviewed_source_revision'] != selection['sourceCommit']:
                raise AuthorityDenied('Qualification covers a different installed code revision')
        dossiers = native.validate(bundle['qualification'], as_of=now, root=self.root,
            provenance_index=bundle['provenance'], campaign_evidence_index=bundle['campaign'],
            target_selection_index=bundle['targetSelection'])
        envelopes = capacity_evidence.validate(bundle['capacity'], as_of=now, root=self.root,
            qindex=bundle['qualification'], provenance_index=bundle['provenance'],
            campaign_evidence_index=bundle['campaign'], target_selection_index=bundle['targetSelection'])
        campaigns = campaign.validate(bundle['campaign'], as_of=now, root=self.root,
                                      target_selection_index=bundle['targetSelection'])
        selected_targets = target_selection.validate(bundle['targetSelection'], as_of=now,
                                                    root=self.root)
        current_targets = {row['selection_id'] for row in selected_targets['records']
                           if row['state'] == 'CURRENT_SELECTED'}
        campaign_by_id = {row['campaign_id']: row for row in campaigns['records']}
        raw_campaign_by_id = {row['campaign_id']: row for row in bundle['campaign']['records']}
        side_for_action, required = _ACTION_CAPABILITIES[operation_kind]
        for side in ('source', 'destination'):
            scope = selection[side]
            platform = _PLATFORM[scope['platformFamily']]
            tuple_value = selection[side + 'Tuple']
            matching = [row for row in dossiers['records']
                        if row['platform'] == platform and row['product_tuple'] == tuple_value
                        and profile in row['assurance_profiles']]
            if len(matching) != 1:
                raise AuthorityDenied('Both directed tuples need exact current guest-profile dossiers')
            dossier = matching[0]
            if side_for_action in (side, 'both'):
                if not required <= set(dossier['qualified_capabilities']):
                    raise AuthorityDenied('Native dossier does not qualify the selected action capabilities')
                assertion = 'ACTION_' + operation_kind
                evidence_pairs = {(item['ref'], item['sha256']) for item in dossier['evidence']}
                supported = False
                for campaign_id in dossier['campaign_evidence_ids']:
                    current = campaign_by_id[campaign_id]
                    if (current['selection_id'] not in current_targets
                            or current['state'] != 'CURRENT_EVIDENCE_COMPLETE'
                            or assertion not in current['latest_passing_assertions']):
                        continue
                    attempts = [item for item in raw_campaign_by_id[campaign_id]['attempts']
                                if item['assertion_id'] == assertion]
                    latest = max(attempts, key=lambda item: target_selection.instant(item['observed_at'], 'observed_at'))
                    if (latest['variant_ref'] == action_variant(selection, operation_kind)
                            and (latest['evidence_ref'], latest['artifact_sha256']) in evidence_pairs):
                        supported = True
                if not supported:
                    raise AuthorityDenied('No current direction/action/profile/code bound native campaign')
            # The destination's commissioned envelope binds the exact dossier,
            # selected topology and site. A platform-wide pass is insufficient.
            if side == 'destination':
                matching_envelopes = [row for row in envelopes['records']
                    if row['platform'] == platform and row['site_id'] == scope['locationId']
                    and row['product_tuple_id'] == dossier['product_tuple_id']
                    and row['qualification_record_id'] == dossier['id']
                    and row['selection_id'] in current_targets]
                if not matching_envelopes:
                    raise AuthorityDenied('Exact destination tuple/site has no commissioned current envelope')
