"""Qualification-campaign evidence assurance tests; no native target contact."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import unittest

from scripts import check_qualification_campaign_assurance as assurance
from scripts import check_qualification_campaign_readiness as readiness
from scripts import check_target_selection_assurance as target

ROOT = Path(__file__).resolve().parents[1]
AS_OF = datetime(2026, 9, 19, 16, 30, tzinfo=timezone.utc)
INTENT = ROOT / 'examples/qualification_campaign_readiness_intent.json.example'


def target_record():
    return {
        'assurance_id': 'TARGET-ASSURANCE-CAMPAIGN-FIXTURE',
        'generation': 1,
        'state': 'CURRENT_SELECTED',
        'selection_id': 'selection-campaign-fixture',
        'scope': {
            'site_ref': 'controlled-site:fixture',
            'cell_ref': 'controlled-cell:fixture',
            'campaign_scope_ref': 'controlled-campaign-scope:fixture',
            'change_authority_ref': 'controlled-authority:change',
            'target_contact_authority_ref': 'controlled-authority:target-contact',
            'target_contact_valid_until': '2026-12-31T23:59:59Z',
            'stop_authority_ref': 'controlled-authority:stop',
            'owner_ref': 'controlled-owner:platform',
            'selected_at': '2026-09-19T15:30:00Z',
            'review_by': '2026-12-31T23:59:59Z'
        },
        'implementation_tuple': {
            'platform_family': 'NUTANIX',
            'product_tuple_id': 'fixture-product-tuple',
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
            'docs/implementation/native-reference/campaign.md'
        ]
    }


def target_index(*records):
    value = target.load()
    value['records'] = list(records)
    return value


def attempt(attempt_id, assertion_id, observation_class, observed_at, *, result='PASSED', control=None):
    evidence_ref = f'controlled-evidence:{attempt_id.lower()}'
    return {
        'attempt_id': attempt_id,
        'assertion_id': assertion_id,
        'procedure_ref': f'controlled-procedure:{assertion_id.lower()}',
        'variant_ref': f'controlled-variant:{attempt_id.lower()}',
        'observation_class': observation_class,
        'result': result,
        'positive_control_attempt_ref': control,
        'evidence_ref': evidence_ref,
        'artifact_sha256': hashlib.sha256(evidence_ref.encode()).hexdigest(),
        'observed_at': observed_at,
        'fresh_until': '2026-12-31T23:59:59Z',
        'reviewer_ref': 'controlled-reviewer:fixture'
    }


def campaign_record(state='CURRENT_EVIDENCE_COMPLETE'):
    return {
        'campaign_id': 'CAMPAIGN-EVIDENCE-FIXTURE-01',
        'generation': 1,
        'state': state,
        'selection_id': 'selection-campaign-fixture',
        'scope': {
            'site_ref': 'controlled-site:fixture',
            'cell_ref': 'controlled-cell:fixture',
            'campaign_scope_ref': 'controlled-campaign-scope:fixture',
            'platform_family': 'NUTANIX',
            'product_tuple_id': 'fixture-product-tuple',
            'service_scope_ref': 'controlled-service:fixture',
            'topology_generation_ref': 'controlled-topology:g1',
            'address_families': ['IPV4', 'IPV6'],
            'failure_scope_ref': 'controlled-failure-scope:fixture',
            'started_at': '2026-09-19T16:00:00Z',
            'review_by': '2026-12-31T23:59:59Z'
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
        'required_assertions': ['W14-01', 'W14-06', 'W14-08'],
        'not_applicable': [],
        'attempts': [
            attempt('ATTEMPT-POS-01', 'W14-01', 'POSITIVE_CONTROL', '2026-09-19T16:05:00Z'),
            attempt('ATTEMPT-NEG-01', 'W14-06', 'NEGATIVE_CONTROL', '2026-09-19T16:10:00Z', control='ATTEMPT-POS-01'),
            attempt('ATTEMPT-REC-01', 'W14-08', 'FAILURE_RECOVERY', '2026-09-19T16:20:00Z')
        ],
        'residual_gaps': [],
        'source_refs': [
            'docs/implementation/native-reference/campaign.md',
            'docs/assurance/qualification-campaign/6-build-an-evidence-packet-a-reviewer-can-challenge.md',
            'docs/engineering/qualification-campaign-evidence-assurance.md'
        ]
    }


def campaign_index(*records):
    value = assurance.load()
    value['records'] = list(records)
    return value


def intent():
    value = readiness.load(INTENT)
    value.update({
        'campaign_id': 'CAMPAIGN-EVIDENCE-FIXTURE-01',
        'selection_id': 'selection-campaign-fixture',
        'site_ref': 'controlled-site:fixture',
        'cell_ref': 'controlled-cell:fixture',
        'campaign_scope_ref': 'controlled-campaign-scope:fixture',
        'platform_family': 'NUTANIX',
        'product_tuple_id': 'fixture-product-tuple',
        'service_scope_ref': 'controlled-service:fixture',
        'topology_generation_ref': 'controlled-topology:g1'
    })
    return value


class QualificationCampaignAssuranceTests(unittest.TestCase):
    def setUp(self):
        self.targets = target_index(target_record())

    def test_empty_index_valid(self):
        result = assurance.validate(assurance.load(), AS_OF, target_selection_index=target.load())
        self.assertEqual(result['record_count'], 0)

    def test_current_complete_campaign_valid(self):
        result = assurance.validate(campaign_index(campaign_record()), AS_OF, target_selection_index=self.targets)
        self.assertEqual(result['current_evidence_complete_count'], 1)
        self.assertEqual(result['retained_attempt_count'], 3)

    def test_campaign_requires_current_selected_target(self):
        with self.assertRaises(ValueError):
            assurance.validate(campaign_index(campaign_record()), AS_OF, target_selection_index=target.load())

    def test_campaign_target_scope_must_match(self):
        record = campaign_record()
        record['scope']['product_tuple_id'] = 'other-tuple'
        with self.assertRaises(ValueError):
            assurance.validate(campaign_index(record), AS_OF, target_selection_index=self.targets)

    def test_current_complete_rejects_missing_assertion(self):
        record = campaign_record()
        record['attempts'] = record['attempts'][:-1]
        with self.assertRaises(ValueError):
            assurance.validate(campaign_index(record), AS_OF, target_selection_index=self.targets)

    def test_reviewed_not_applicable_can_close_one_assertion(self):
        record = campaign_record()
        record['attempts'] = record['attempts'][:-1]
        record['not_applicable'] = [{
            'assertion_id': 'W14-08',
            'decision_ref': 'controlled-decision:w14-08-na',
            'reason_ref': 'controlled-rationale:w14-08-na',
            'reviewer_ref': 'controlled-reviewer:fixture',
            'review_by': '2026-12-31T23:59:59Z'
        }]
        result = assurance.validate(campaign_index(record), AS_OF, target_selection_index=self.targets)
        self.assertEqual(result['current_evidence_complete_count'], 1)

    def test_negative_control_requires_healthy_positive_control(self):
        record = campaign_record()
        record['attempts'][0]['result'] = 'FAILED'
        with self.assertRaises(ValueError):
            assurance.validate(campaign_index(record), AS_OF, target_selection_index=self.targets)

    def test_negative_control_requires_explicit_positive_control_reference(self):
        record = campaign_record()
        record['attempts'][1]['positive_control_attempt_ref'] = None
        with self.assertRaises(ValueError):
            assurance.validate(campaign_index(record), AS_OF, target_selection_index=self.targets)

    def test_prior_failure_is_retained_and_later_pass_can_be_current(self):
        record = campaign_record()
        record['attempts'].insert(
            2, attempt('ATTEMPT-NEG-00', 'W14-06', 'NEGATIVE_CONTROL',
                       '2026-09-19T16:08:00Z', result='FAILED', control='ATTEMPT-POS-01')
        )
        result = assurance.validate(campaign_index(record), AS_OF, target_selection_index=self.targets)
        self.assertEqual(result['records'][0]['attempt_count'], 4)
        self.assertNotIn('W14-06', result['records'][0]['nonpassing_assertions'])

    def test_latest_failure_blocks_current_complete(self):
        record = campaign_record()
        record['attempts'].append(
            attempt('ATTEMPT-NEG-02', 'W14-06', 'NEGATIVE_CONTROL',
                    '2026-09-19T16:25:00Z', result='FAILED', control='ATTEMPT-POS-01')
        )
        with self.assertRaises(ValueError):
            assurance.validate(campaign_index(record), AS_OF, target_selection_index=self.targets)

    def test_expired_evidence_requires_noncurrent_state(self):
        record = campaign_record()
        record['attempts'][2]['fresh_until'] = '2026-09-19T16:29:59Z'
        with self.assertRaises(ValueError):
            assurance.validate(campaign_index(record), AS_OF, target_selection_index=self.targets)
        record['state'] = 'REVIEW_DUE'
        result = assurance.validate(campaign_index(record), AS_OF, target_selection_index=self.targets)
        self.assertEqual(result['review_due_count'], 1)

    def test_open_gap_requires_gaps_open_state(self):
        gap = {
            'gap_id': 'CAMPAIGN-GAP-01',
            'status': 'OPEN',
            'owner_ref': 'controlled-owner:campaign',
            'treatment_ref': 'controlled-treatment:campaign-gap',
            'decision_ref': None,
            'review_by': '2026-12-31T23:59:59Z'
        }
        record = campaign_record()
        record['residual_gaps'].append(gap)
        with self.assertRaises(ValueError):
            assurance.validate(campaign_index(record), AS_OF, target_selection_index=self.targets)
        record['state'] = 'GAPS_OPEN'
        result = assurance.validate(campaign_index(record), AS_OF, target_selection_index=self.targets)
        self.assertEqual(result['gaps_open_count'], 1)

    def test_authority_cannot_be_embedded(self):
        for key in ('qualification_decision_status', 'production_authority_status'):
            with self.subTest(key=key):
                record = campaign_record()
                record['governance'][key] = 'APPROVED'
                with self.assertRaises(ValueError):
                    assurance.validate(campaign_index(record), AS_OF, target_selection_index=self.targets)

    def test_duplicate_attempt_rejected(self):
        record = campaign_record()
        record['attempts'].append(deepcopy(record['attempts'][0]))
        with self.assertRaises(ValueError):
            assurance.validate(campaign_index(record), AS_OF, target_selection_index=self.targets)

    def test_cli_empty_index_grants_no_authority(self):
        run = subprocess.run([
            sys.executable, str(ROOT / 'scripts/check_qualification_campaign_assurance.py'),
            '--as-of', '2026-09-19T16:30:00Z'
        ], capture_output=True, text=True, timeout=10)
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        output = json.loads(run.stdout)
        self.assertEqual(output['record_count'], 0)
        for key in (
            'may_contact_target', 'may_retrieve_credentials', 'may_run_native_tests',
            'may_issue_qualification', 'may_update_platform_registry', 'may_apply', 'may_activate'
        ):
            self.assertIs(output[key], False)


class QualificationCampaignReadinessTests(unittest.TestCase):
    def setUp(self):
        self.targets = target_index(target_record())

    def test_empty_index_holds(self):
        result = readiness.evaluate(
            readiness.load(INTENT), assurance.load(),
            target_selection_index=target.load(), as_of=AS_OF
        )
        self.assertEqual(result['status'], readiness.HOLD_NONE)

    def test_complete_packet_is_review_ready_only(self):
        result = readiness.evaluate(
            intent(), campaign_index(campaign_record()),
            target_selection_index=self.targets, as_of=AS_OF
        )
        self.assertEqual(result['status'], readiness.READY)
        self.assertFalse(result['may_issue_qualification'])
        self.assertFalse(result['may_run_native_tests'])

    def test_scope_mismatch_holds(self):
        value = intent()
        value['topology_generation_ref'] = 'controlled-topology:g2'
        result = readiness.evaluate(
            value, campaign_index(campaign_record()),
            target_selection_index=self.targets, as_of=AS_OF
        )
        self.assertEqual(result['status'], readiness.HOLD_SCOPE)

    def test_readiness_intent_cannot_claim_authority(self):
        value = intent()
        value['qualification_decision'] = 'APPROVED'
        with self.assertRaises(ValueError):
            readiness.evaluate(
                value, campaign_index(campaign_record()),
                target_selection_index=self.targets, as_of=AS_OF
            )

    def test_cli_empty_index_holds(self):
        run = subprocess.run([
            sys.executable, str(ROOT / 'scripts/check_qualification_campaign_readiness.py'),
            str(INTENT), '--as-of', '2026-09-19T16:30:00Z',
            '--expected-status', readiness.HOLD_NONE
        ], capture_output=True, text=True, timeout=10)
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        self.assertEqual(json.loads(run.stdout)['status'], readiness.HOLD_NONE)


if __name__ == '__main__':
    unittest.main()
