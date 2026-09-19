"""Synthetic qualification-chain fixtures for repository tests only."""
from __future__ import annotations

import hashlib

from scripts import check_qualification_campaign_assurance as campaign
from scripts import check_target_selection_assurance as target

PLATFORM_TO_CAMPAIGN = {
    'nutanix': 'NUTANIX',
    'vmware-nsx': 'VMWARE_NSX',
    'openstack': 'OPENSTACK',
}


def target_record(platform='nutanix', tuple_id='fixture-tuple', *,
                  selection_id='selection-fixture', site_ref='controlled-site:fixture',
                  cell_ref='controlled-cell:fixture',
                  campaign_scope_ref='controlled-campaign-scope:fixture'):
    return {
        'assurance_id': 'TARGET-' + selection_id.upper().replace(':', '-'),
        'generation': 1,
        'state': 'CURRENT_SELECTED',
        'selection_id': selection_id,
        'scope': {
            'site_ref': site_ref,
            'cell_ref': cell_ref,
            'campaign_scope_ref': campaign_scope_ref,
            'change_authority_ref': 'controlled-authority:change',
            'target_contact_authority_ref': 'controlled-authority:target-contact',
            'target_contact_valid_until': '2026-12-31T23:59:59Z',
            'stop_authority_ref': 'controlled-authority:stop',
            'owner_ref': 'controlled-owner:platform',
            'selected_at': '2026-09-17T08:00:00Z',
            'review_by': '2026-12-31T23:59:59Z'
        },
        'implementation_tuple': {
            'platform_family': PLATFORM_TO_CAMPAIGN[platform],
            'product_tuple_id': tuple_id,
            'hardware_inventory_ref': 'controlled-target:hardware',
            'product_api_provider_ref': 'controlled-target:product-api-provider',
            'feature_entitlement_ref': 'controlled-target:feature-entitlement',
            'version_source_provenance_ref': 'controlled-target:version-provenance',
            'security_edge_realization_ref': 'controlled-target:security-edge',
            'management_oob_ref': 'controlled-target:management-oob',
            'network_backend_ref': 'controlled-target:network-backend',
            'storage_backend_ref': 'controlled-target:storage-backend'
        },
        'campaign': {
            'qualification_campaign_ref': 'controlled-campaign:qualification',
            'native_api_scope_ref': 'controlled-campaign:native-api',
            'observer_scope_ref': 'controlled-campaign:observer',
            'writer_scope_ref': 'controlled-campaign:writer',
            'credential_custody_ref': 'controlled-campaign:credential-custody',
            'evidence_workspace_ref': 'controlled-campaign:evidence-workspace',
            'data_restriction_ref': 'controlled-campaign:no-production-data',
            'permitted_operations_ref': 'controlled-campaign:permitted',
            'prohibited_operations_ref': 'controlled-campaign:prohibited',
            'cleanup_ref': 'controlled-campaign:cleanup',
            'contact_window_ref': 'controlled-campaign:window',
            'production_authority_status': 'NOT_ISSUED'
        },
        'residual_gaps': [],
        'source_refs': [
            'docs/engineering/actual-target-selection-assurance.md',
            'docs/engineering/qualification-campaign-evidence-assurance.md'
        ]
    }


def target_index(platform='nutanix', tuple_id='fixture-tuple', **kwargs):
    value = target.load()
    value['records'] = [target_record(platform, tuple_id, **kwargs)]
    return value


def campaign_record(evidence_refs, platform='nutanix', tuple_id='fixture-tuple', *,
                    campaign_id='CAMPAIGN-FIXTURE-01', selection_id='selection-fixture',
                    site_ref='controlled-site:fixture', cell_ref='controlled-cell:fixture',
                    campaign_scope_ref='controlled-campaign-scope:fixture'):
    attempts = []
    assertions = []
    for number, ref in enumerate(evidence_refs, 1):
        assertion_id = f'W14-FIXTURE-{number:02d}'
        attempt_id = f'ATTEMPT-FIXTURE-{number:02d}'
        assertions.append(assertion_id)
        attempts.append({
            'attempt_id': attempt_id,
            'assertion_id': assertion_id,
            'procedure_ref': f'controlled-procedure:fixture-{number:02d}',
            'variant_ref': f'controlled-variant:fixture-{number:02d}',
            'observation_class': 'OTHER',
            'result': 'PASSED',
            'positive_control_attempt_ref': None,
            'evidence_ref': ref,
            'artifact_sha256': hashlib.sha256(ref.encode()).hexdigest(),
            'observed_at': '2026-09-17T10:00:00Z',
            'fresh_until': '2026-12-31T23:59:59Z',
            'reviewer_ref': 'controlled-reviewer:fixture'
        })
    return {
        'campaign_id': campaign_id,
        'generation': 1,
        'state': 'CURRENT_EVIDENCE_COMPLETE',
        'selection_id': selection_id,
        'scope': {
            'site_ref': site_ref,
            'cell_ref': cell_ref,
            'campaign_scope_ref': campaign_scope_ref,
            'platform_family': PLATFORM_TO_CAMPAIGN[platform],
            'product_tuple_id': tuple_id,
            'service_scope_ref': 'controlled-service:fixture',
            'topology_generation_ref': 'controlled-topology:g1',
            'address_families': ['IPV4'],
            'failure_scope_ref': 'controlled-failure-scope:fixture',
            'started_at': '2026-09-17T09:00:00Z',
            'review_by': '2026-12-31T23:59:59Z'
        },
        'authorization': {
            'change_authority_ref': 'controlled-authority:change',
            'target_contact_authority_ref': 'controlled-authority:target-contact',
            'target_contact_valid_until': '2026-12-31T23:59:59Z',
            'stop_authority_ref': 'controlled-authority:stop',
            'qualification_campaign_ref': 'controlled-campaign:qualification',
            'native_api_scope_ref': 'controlled-campaign:native-api',
            'observer_scope_ref': 'controlled-campaign:observer',
            'writer_scope_ref': 'controlled-campaign:writer',
            'credential_custody_ref': 'controlled-campaign:credential-custody',
            'evidence_workspace_ref': 'controlled-campaign:evidence-workspace',
            'data_restriction_ref': 'controlled-campaign:no-production-data',
            'permitted_operations_ref': 'controlled-campaign:permitted',
            'prohibited_operations_ref': 'controlled-campaign:prohibited',
            'cleanup_ref': 'controlled-campaign:cleanup',
            'contact_window_ref': 'controlled-campaign:window'
        },
        'governance': {
            'applicability_ref': 'controlled-campaign:applicability',
            'run_sheet_ref': 'controlled-campaign:run-sheet',
            'authorized_fault_scope_ref': 'controlled-authority:fault-scope',
            'evidence_workspace_ref': 'controlled-campaign:evidence-workspace',
            'artifact_manifest_ref': 'controlled-campaign:artifact-manifest',
            'reviewer_ref': 'controlled-reviewer:fixture',
            'qualification_decision_status': 'NOT_ISSUED',
            'production_authority_status': 'NOT_ISSUED'
        },
        'required_assertions': assertions,
        'not_applicable': [],
        'attempts': attempts,
        'residual_gaps': [],
        'source_refs': [
            'docs/implementation/native-reference/campaign.md',
            'docs/engineering/qualification-campaign-evidence-assurance.md'
        ]
    }


def campaign_index(evidence_refs, platform='nutanix', tuple_id='fixture-tuple', **kwargs):
    value = campaign.load()
    value['records'] = [campaign_record(evidence_refs, platform, tuple_id, **kwargs)]
    return value
