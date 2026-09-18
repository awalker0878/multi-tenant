"""Security-edge/ZIP assurance tests; no firewall, route or attachment mutation."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
import unittest

from scripts import check_security_edge_zip_assurance as assurance
from scripts import check_security_edge_zip_readiness as readiness

ROOT=Path(__file__).resolve().parents[1]
AS_OF=datetime(2026,9,18,21,45,tzinfo=timezone.utc)
INTENT=ROOT/'examples/security_edge_zip_readiness_intent.json.example'


def functions():
    return {key:f'controlled-zip-function:{key}' for key in sorted(assurance.FUNCTION_KEYS)}


def accepted_gap():
    return {
        'gap_id':'ZIP-GAP-ACCEPTED-01',
        'status':'ACCEPTED',
        'owner_ref':'controlled-owner:zip',
        'treatment_ref':'controlled-treatment:zip-gap',
        'decision_ref':'controlled-decision:zip-gap-accepted',
        'review_by':'2026-12-31T23:59:59Z',
    }


def open_gap():
    return {
        'gap_id':'ZIP-GAP-OPEN-01',
        'status':'OPEN',
        'owner_ref':'controlled-owner:zip',
        'treatment_ref':'controlled-treatment:zip-gap-open',
        'decision_ref':None,
        'review_by':'2026-12-31T23:59:59Z',
    }


def record(state='CURRENT_QUALIFIED',realization='DEDICATED_EDGE'):
    distributed=realization=='DISTRIBUTED_SHARED'
    return {
        'assurance_id':'ZIP-ASSURANCE-FIXTURE-01',
        'generation':1,
        'state':state,
        'boundary_id':'zip-fixture-01',
        'scope':{
            'source_endpoint_ref':'controlled-domain-endpoint:oz-fixture',
            'destination_endpoint_ref':'controlled-domain-endpoint:rz-fixture',
            'source_authority_ref':'controlled-authority:oz',
            'destination_authority_ref':'controlled-authority:rz',
            'joint_approval_ref':'controlled-approval:zip-fixture',
            'service_class_ref':'controlled-service-class:zip-fixture',
            'management_authority_ref':'controlled-authority:edge-management',
            'accepted_at':'2026-09-18T18:00:00Z',
            'review_by':'2026-12-31T23:59:59Z',
        },
        'realization':{
            'type':realization,
            'sharing_assurance_ref':'controlled-assurance:shared-zip' if distributed else None,
            'equivalent_outcomes_ref':'controlled-evidence:zip-equivalence' if distributed else None,
            'unsupported_mandatory_functions':[],
        },
        'security_functions':functions(),
        'topology':{
            'forward_path_ref':'controlled-path:forward',
            'reply_path_ref':'controlled-path:reply',
            'attachment_pair_ref':'controlled-attachments:pair',
            'native_route_review_ref':'controlled-review:native-routes',
            'bypass_review_ref':'controlled-review:bypass-paths',
            'management_path_ref':'controlled-path:management',
            'translation_behavior_ref':'controlled-behavior:translation-none',
            'return_symmetry_ref':'controlled-evidence:return-symmetry',
        },
        'policy':{
            'deny_baseline_ref':'controlled-policy:deny-baseline',
            'approved_flow_set_ref':'controlled-policy:approved-flows',
            'policy_precedence_ref':'controlled-policy:precedence',
            'inspection_profile_ref':'controlled-profile:inspection',
            'logging_profile_ref':'controlled-profile:logging',
            'session_revocation_ref':'controlled-profile:session-revocation',
        },
        'failure_tests':{
            'ha_mode_ref':'controlled-ha:mode',
            'state_sync_ref':'controlled-ha:state-sync',
            'edge_member_loss_ref':'controlled-test:edge-member-loss',
            'manager_unavailable_ref':'controlled-test:manager-unavailable',
            'route_withdrawal_ref':'controlled-test:route-withdrawal',
            'no_uninspected_fallback_ref':'controlled-test:no-uninspected-fallback',
            'observed_at':'2026-09-18T20:00:00Z',
            'valid_until':'2026-12-31T23:59:59Z',
        },
        'capacity':{
            'session_capacity_ref':'controlled-capacity:sessions',
            'throughput_ref':'controlled-capacity:throughput',
            'inspection_capacity_ref':'controlled-capacity:inspection',
            'log_export_capacity_ref':'controlled-capacity:log-export',
            'survivor_capacity_ref':'controlled-capacity:survivor',
        },
        'path_tests':{
            'allowed_flow_ref':'controlled-test:allowed-flow',
            'cross_tenant_deny_ref':'controlled-test:cross-tenant-deny',
            'unsolicited_reverse_deny_ref':'controlled-test:unsolicited-reverse',
            'management_transit_deny_ref':'controlled-test:management-transit-deny',
            'same_host_or_distributed_bypass_ref':'controlled-test:bypass-negative',
            'observed_at':'2026-09-18T20:10:00Z',
            'valid_until':'2026-12-31T23:59:59Z',
        },
        'residual_gaps':[accepted_gap()],
        'source_refs':[
            'docs/architecture/reference/8-zone-interfaces-routing-and-security-edge-topology.md',
            'docs/engineering/fabric/3-worked-inter-zone-routing-and-enforcement-schedule.md',
            'docs/implementation/allocation/zip.md',
            'docs/engineering/security-edge-zip-assurance.md',
        ],
    }


def index(*records):
    value=assurance.load()
    value['records']=list(records)
    return value


def intent():
    value=readiness.load(INTENT)
    value['boundary_id']='zip-fixture-01'
    value['source_endpoint_ref']='controlled-domain-endpoint:oz-fixture'
    value['destination_endpoint_ref']='controlled-domain-endpoint:rz-fixture'
    value['service_class_ref']='controlled-service-class:zip-fixture'
    return value


class SecurityEdgeAssuranceTests(unittest.TestCase):
    def test_current_index_is_valid_empty(self):
        self.assertEqual(assurance.validate(assurance.load(),as_of=AS_OF)['record_count'],0)

    def test_current_dedicated_edge_record_is_valid(self):
        self.assertEqual(assurance.validate(index(record()),as_of=AS_OF)['current_qualified_count'],1)

    def test_current_distributed_shared_record_requires_equivalence_and_is_valid(self):
        self.assertEqual(
            assurance.validate(index(record(realization='DISTRIBUTED_SHARED')),as_of=AS_OF)['current_qualified_count'],1)

    def test_two_distinct_adjacent_endpoints_are_required(self):
        r=record()
        r['scope']['destination_endpoint_ref']=r['scope']['source_endpoint_ref']
        with self.assertRaises(ValueError):
            assurance.validate(index(r),as_of=AS_OF)

    def test_same_organizational_authority_can_own_both_endpoints(self):
        r=record()
        r['scope']['destination_authority_ref']=r['scope']['source_authority_ref']
        self.assertEqual(assurance.validate(index(r),as_of=AS_OF)['current_qualified_count'],1)

    def test_distributed_shared_requires_equivalent_outcome_evidence(self):
        r=record(realization='DISTRIBUTED_SHARED')
        r['realization']['equivalent_outcomes_ref']=None
        with self.assertRaises(ValueError):
            assurance.validate(index(r),as_of=AS_OF)

    def test_unsupported_mandatory_function_makes_zip_ineligible(self):
        r=record()
        r['realization']['unsupported_mandatory_functions']=['inspection']
        with self.assertRaises(ValueError):
            assurance.validate(index(r),as_of=AS_OF)

    def test_complete_security_function_set_is_required(self):
        r=record()
        r['security_functions'].pop('inspection')
        with self.assertRaises(ValueError):
            assurance.validate(index(r),as_of=AS_OF)

    def test_bypass_review_is_mandatory(self):
        r=record()
        r['topology']['bypass_review_ref']=''
        with self.assertRaises(ValueError):
            assurance.validate(index(r),as_of=AS_OF)

    def test_current_qualified_rejects_expired_failure_evidence(self):
        r=record()
        r['failure_tests']['valid_until']='2026-09-18T21:44:59Z'
        with self.assertRaises(ValueError):
            assurance.validate(index(r),as_of=AS_OF)

    def test_failure_test_due_requires_expired_path_or_failure_evidence(self):
        r=record(state='FAILURE_TEST_DUE')
        r['path_tests']['valid_until']='2026-09-18T21:44:59Z'
        self.assertEqual(assurance.validate(index(r),as_of=AS_OF)['failure_test_due_count'],1)

    def test_review_due_requires_expired_scope_or_gap_review(self):
        r=record(state='REVIEW_DUE')
        r['scope']['review_by']='2026-09-18T21:44:59Z'
        self.assertEqual(assurance.validate(index(r),as_of=AS_OF)['review_due_count'],1)

    def test_current_qualified_cannot_have_open_gap(self):
        r=record()
        r['residual_gaps'].append(open_gap())
        with self.assertRaises(ValueError):
            assurance.validate(index(r),as_of=AS_OF)

    def test_gaps_open_requires_open_gap(self):
        r=record(state='GAPS_OPEN')
        r['residual_gaps'].append(open_gap())
        self.assertEqual(assurance.validate(index(r),as_of=AS_OF)['gaps_open_count'],1)

    def test_open_gap_cannot_carry_acceptance_decision(self):
        r=record(state='GAPS_OPEN')
        gap=open_gap()
        gap['decision_ref']='controlled-decision:premature'
        r['residual_gaps'].append(gap)
        with self.assertRaises(ValueError):
            assurance.validate(index(r),as_of=AS_OF)

    def test_cli_empty_index_grants_no_edge_authority(self):
        run=subprocess.run([
            sys.executable,str(ROOT/'scripts/check_security_edge_zip_assurance.py'),
            '--as-of','2026-09-18T21:45:00Z',
        ],capture_output=True,text=True,timeout=10)
        self.assertEqual(run.returncode,0,run.stdout+run.stderr)
        out=json.loads(run.stdout)
        self.assertEqual(out['record_count'],0)
        for key in ('may_create_route','may_change_policy','may_attach_domain',
                    'may_change_edge','may_change_management_access','may_apply','may_activate'):
            self.assertIs(out[key],False)


class SecurityEdgeReadinessTests(unittest.TestCase):
    def test_current_example_holds_without_zip_assurance(self):
        result=readiness.evaluate(readiness.load(INTENT),index=assurance.load(),as_of=AS_OF)
        self.assertEqual(result['status'],readiness.HOLD_NONE)

    def test_current_zip_satisfies_only_readiness_prerequisite(self):
        result=readiness.evaluate(intent(),index=index(record()),as_of=AS_OF)
        self.assertEqual(result['status'],readiness.READY)
        for key in ('may_create_route','may_change_policy','may_attach_domain',
                    'may_change_edge','may_change_management_access','may_apply','may_activate'):
            self.assertIs(result[key],False)

    def test_review_due_holds(self):
        r=record(state='REVIEW_DUE')
        r['scope']['review_by']='2026-09-18T21:44:59Z'
        self.assertEqual(readiness.evaluate(intent(),index=index(r),as_of=AS_OF)['status'],readiness.HOLD_REVIEW)

    def test_failure_test_due_holds(self):
        r=record(state='FAILURE_TEST_DUE')
        r['failure_tests']['valid_until']='2026-09-18T21:44:59Z'
        self.assertEqual(readiness.evaluate(intent(),index=index(r),as_of=AS_OF)['status'],readiness.HOLD_FAILURE)

    def test_open_gap_holds(self):
        r=record(state='GAPS_OPEN')
        r['residual_gaps'].append(open_gap())
        self.assertEqual(readiness.evaluate(intent(),index=index(r),as_of=AS_OF)['status'],readiness.HOLD_GAPS)

    def test_uncertain_holds(self):
        self.assertEqual(
            readiness.evaluate(intent(),index=index(record(state='UNCERTAIN')),as_of=AS_OF)['status'],
            readiness.HOLD_UNCERTAIN)

    def test_boundary_scope_mismatch_holds(self):
        value=intent()
        value['destination_endpoint_ref']='controlled-domain-endpoint:other'
        self.assertEqual(readiness.evaluate(value,index=index(record()),as_of=AS_OF)['status'],readiness.HOLD_SCOPE)

    def test_caller_cannot_carry_production_authority(self):
        value=intent()
        value['production_authority']='APPROVED'
        with self.assertRaises(ValueError):
            readiness.evaluate(value,index=index(record()),as_of=AS_OF)

    def test_cli_can_assert_current_empty_hold(self):
        run=subprocess.run([
            sys.executable,str(ROOT/'scripts/check_security_edge_zip_readiness.py'),str(INTENT),
            '--as-of','2026-09-18T21:45:00Z',
            '--expected-status',readiness.HOLD_NONE,
        ],capture_output=True,text=True,timeout=10)
        self.assertEqual(run.returncode,0,run.stdout+run.stderr)
        self.assertEqual(json.loads(run.stdout)['status'],readiness.HOLD_NONE)


if __name__=='__main__':
    unittest.main()
