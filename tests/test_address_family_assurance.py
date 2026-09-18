"""Native IPv6/address-family assurance tests; no address, route or policy mutation."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
import unittest

from scripts import check_address_family_assurance as assurance
from scripts import check_address_family_readiness as readiness

ROOT=Path(__file__).resolve().parents[1]
AS_OF=datetime(2026,9,18,22,45,tzinfo=timezone.utc)
INTENT=ROOT/'examples/address_family_readiness_intent.json.example'


def accepted_gap():
    return {
        'gap_id':'AF-GAP-ACCEPTED-01',
        'status':'ACCEPTED',
        'owner_ref':'controlled-owner:network',
        'treatment_ref':'controlled-treatment:address-family-gap',
        'decision_ref':'controlled-decision:address-family-gap-accepted',
        'review_by':'2026-12-31T23:59:59Z',
    }


def open_gap():
    return {
        'gap_id':'AF-GAP-OPEN-01',
        'status':'OPEN',
        'owner_ref':'controlled-owner:network',
        'treatment_ref':'controlled-treatment:address-family-gap-open',
        'decision_ref':None,
        'review_by':'2026-12-31T23:59:59Z',
    }


def record(state='CURRENT_QUALIFIED',mode='DUAL_STACK',platform='NUTANIX'):
    families=list(assurance.MODES[mode])
    return {
        'assurance_id':'AF-ASSURANCE-FIXTURE-01',
        'generation':1,
        'state':state,
        'qualification_id':'af-qualification-fixture-01',
        'platform':platform,
        'scope':{
            'offered_mode':mode,
            'offered_families':families,
            'service_class_ref':'controlled-service-class:fixture',
            'platform_profile_ref':'controlled-platform-profile:fixture',
            'platform_qualification_ref':'controlled-platform-qualification:fixture',
            'security_edge_assurance_refs':['controlled-zip-assurance:fixture'],
            'accepted_at':'2026-09-18T20:00:00Z',
            'review_by':'2026-12-31T23:59:59Z',
            'owner_ref':'controlled-owner:network-engineering',
        },
        'native_path':{
            'routing_ref':'controlled-ipv6:routing',
            'same_host_enforcement_ref':'controlled-ipv6:same-host-enforcement',
            'source_neighbor_control_ref':'controlled-ipv6:source-neighbor-control',
            'address_assignment_ref':'controlled-ipv6:address-assignment',
            'local_protocol_control_ref':'controlled-ipv6:local-protocol-control',
            'transition_restriction_ref':'controlled-ipv6:transition-restriction',
            'management_exclusion_ref':'controlled-ipv6:management-exclusion',
            'observed_at':'2026-09-18T21:00:00Z',
            'valid_until':'2026-12-31T23:59:59Z',
        },
        'security_equivalence':{
            'ipv4_baseline_ref':'controlled-family-baseline:ipv4',
            'policy_equivalence_ref':'controlled-family-equivalence:policy',
            'negative_path_ref':'controlled-family-test:negative-path',
            'inspection_equivalence_ref':'controlled-family-equivalence:inspection',
            'logging_attribution_ref':'controlled-family-equivalence:logging',
            'fail_secure_ref':'controlled-family-equivalence:fail-secure',
            'observed_at':'2026-09-18T21:05:00Z',
            'valid_until':'2026-12-31T23:59:59Z',
        },
        'shared_services':{
            'dns_aaaa_ref':'controlled-service-evidence:dns-aaaa',
            'dns_udp_tcp_ref':'controlled-service-evidence:dns-udp-tcp',
            'time_service_ref':'controlled-service-evidence:time',
            'trust_identity_ref':'controlled-service-evidence:trust-identity',
            'telemetry_ref':'controlled-service-evidence:telemetry',
            'image_repository_ref':'controlled-service-evidence:image-repository',
            'protection_recovery_ref':'controlled-service-evidence:protection-recovery',
            'origin_specific_reply_ref':'controlled-service-evidence:origin-specific-reply',
            'observed_at':'2026-09-18T21:10:00Z',
            'valid_until':'2026-12-31T23:59:59Z',
        },
        'pmtu':{
            'effective_workload_mtu_ref':'controlled-mtu:workload',
            'encapsulation_budget_ref':'controlled-mtu:encapsulation',
            'icmpv6_error_policy_ref':'controlled-mtu:icmpv6-policy',
            'packet_too_big_ref':'controlled-mtu:packet-too-big',
            'large_small_control_ref':'controlled-mtu:large-small-control',
            'fragment_extension_policy_ref':'controlled-mtu:fragment-extension-policy',
            'observed_at':'2026-09-18T21:15:00Z',
            'valid_until':'2026-12-31T23:59:59Z',
        },
        'failure_recovery':{
            'route_withdrawal_ref':'controlled-failure:route-withdrawal',
            'edge_failure_ref':'controlled-failure:edge',
            'service_reply_loss_ref':'controlled-failure:service-reply-loss',
            'address_dad_recovery_ref':'controlled-failure:address-dad-recovery',
            'no_ipv4_fallback_ref':'controlled-failure:no-ipv4-fallback',
            'survivor_capacity_ref':'controlled-failure:survivor-capacity',
            'observed_at':'2026-09-18T21:20:00Z',
            'valid_until':'2026-12-31T23:59:59Z',
        },
        'operations':{
            'monitoring_ref':'controlled-operations:ipv6-monitoring',
            'runbook_ref':'controlled-operations:ipv6-runbook',
            'recovery_reexposure_ref':'controlled-operations:ipv6-reexposure',
            'operational_acceptance_ref':'controlled-operations:ipv6-acceptance',
            'observed_at':'2026-09-18T21:25:00Z',
            'valid_until':'2026-12-31T23:59:59Z',
        },
        'residual_gaps':[accepted_gap()],
        'source_refs':[
            'docs/engineering/routed-ipv6-qualification.md',
            'docs/implementation/routed-ipv6-lab.md',
            'docs/engineering/native-ipv6-address-family-assurance.md',
        ],
    }


def index(*records):
    value=assurance.load()
    value['records']=list(records)
    return value


def intent(mode='DUAL_STACK',platform='NUTANIX'):
    value=readiness.load(INTENT)
    value['qualification_id']='af-qualification-fixture-01'
    value['platform']=platform
    value['offered_mode']=mode
    value['offered_families']=list(assurance.MODES[mode])
    value['service_class_ref']='controlled-service-class:fixture'
    value['platform_profile_ref']='controlled-platform-profile:fixture'
    return value


class AddressFamilyAssuranceTests(unittest.TestCase):
    def test_current_index_is_valid_empty(self):
        self.assertEqual(assurance.validate(assurance.load(),as_of=AS_OF)['record_count'],0)

    def test_current_dual_stack_record_is_valid(self):
        self.assertEqual(assurance.validate(index(record()),as_of=AS_OF)['current_qualified_count'],1)

    def test_current_ipv6_only_record_is_valid(self):
        self.assertEqual(
            assurance.validate(index(record(mode='IPV6_ONLY')),as_of=AS_OF)['current_qualified_count'],1)

    def test_supported_platform_labels_are_valid(self):
        for platform in sorted(assurance.PLATFORMS):
            with self.subTest(platform=platform):
                self.assertEqual(
                    assurance.validate(index(record(platform=platform)),as_of=AS_OF)['current_qualified_count'],1)

    def test_mode_and_family_set_must_match_exactly(self):
        r=record()
        r['scope']['offered_families']=['IPV6','IPV4']
        with self.assertRaises(ValueError):
            assurance.validate(index(r),as_of=AS_OF)

    def test_security_edge_assurance_reference_is_required(self):
        r=record()
        r['scope']['security_edge_assurance_refs']=[]
        with self.assertRaises(ValueError):
            assurance.validate(index(r),as_of=AS_OF)

    def test_complete_native_path_evidence_is_required(self):
        r=record()
        r['native_path'].pop('local_protocol_control_ref')
        with self.assertRaises(ValueError):
            assurance.validate(index(r),as_of=AS_OF)

    def test_complete_shared_service_dependencies_are_required(self):
        r=record()
        r['shared_services'].pop('protection_recovery_ref')
        with self.assertRaises(ValueError):
            assurance.validate(index(r),as_of=AS_OF)

    def test_pmtu_requires_packet_too_big_evidence(self):
        r=record()
        r['pmtu']['packet_too_big_ref']=''
        with self.assertRaises(ValueError):
            assurance.validate(index(r),as_of=AS_OF)

    def test_current_qualified_rejects_stale_packet_evidence(self):
        r=record()
        r['pmtu']['valid_until']='2026-09-18T22:44:59Z'
        with self.assertRaises(ValueError):
            assurance.validate(index(r),as_of=AS_OF)

    def test_packet_test_due_accepts_stale_packet_evidence_only(self):
        r=record('PACKET_TEST_DUE')
        r['failure_recovery']['valid_until']='2026-09-18T22:44:59Z'
        self.assertEqual(assurance.validate(index(r),as_of=AS_OF)['packet_test_due_count'],1)

    def test_dependency_due_accepts_stale_service_evidence_only(self):
        r=record('DEPENDENCY_DUE')
        r['shared_services']['valid_until']='2026-09-18T22:44:59Z'
        self.assertEqual(assurance.validate(index(r),as_of=AS_OF)['dependency_due_count'],1)

    def test_review_due_requires_expired_review(self):
        r=record('REVIEW_DUE')
        r['scope']['review_by']='2026-09-18T22:44:59Z'
        self.assertEqual(assurance.validate(index(r),as_of=AS_OF)['review_due_count'],1)

    def test_current_qualified_cannot_have_open_gap(self):
        r=record()
        r['residual_gaps'].append(open_gap())
        with self.assertRaises(ValueError):
            assurance.validate(index(r),as_of=AS_OF)

    def test_gaps_open_requires_open_gap(self):
        r=record('GAPS_OPEN')
        r['residual_gaps'].append(open_gap())
        self.assertEqual(assurance.validate(index(r),as_of=AS_OF)['gaps_open_count'],1)

    def test_duplicate_qualification_id_rejected(self):
        one=record()
        two=deepcopy(one)
        two['assurance_id']='AF-ASSURANCE-FIXTURE-02'
        with self.assertRaises(ValueError):
            assurance.validate(index(one,two),as_of=AS_OF)

    def test_cli_empty_index_grants_no_network_authority(self):
        run=subprocess.run([
            sys.executable,str(ROOT/'scripts/check_address_family_assurance.py'),
            '--as-of','2026-09-18T22:45:00Z',
        ],capture_output=True,text=True,timeout=10)
        self.assertEqual(run.returncode,0,run.stdout+run.stderr)
        out=json.loads(run.stdout)
        self.assertEqual(out['record_count'],0)
        for key in ('may_allocate_address','may_enable_ipv6','may_change_route',
                    'may_change_policy','may_change_shared_service','may_apply','may_activate'):
            self.assertIs(out[key],False)


class AddressFamilyReadinessTests(unittest.TestCase):
    def test_current_example_holds_without_assurance(self):
        result=readiness.evaluate(readiness.load(INTENT),index=assurance.load(),as_of=AS_OF)
        self.assertEqual(result['status'],readiness.HOLD_NONE)

    def test_current_dual_stack_satisfies_only_readiness_prerequisite(self):
        result=readiness.evaluate(intent(),index=index(record()),as_of=AS_OF)
        self.assertEqual(result['status'],readiness.READY)
        for key in ('may_allocate_address','may_enable_ipv6','may_change_route',
                    'may_change_policy','may_change_shared_service','may_apply','may_activate'):
            self.assertIs(result[key],False)

    def test_packet_due_holds(self):
        r=record('PACKET_TEST_DUE')
        r['pmtu']['valid_until']='2026-09-18T22:44:59Z'
        self.assertEqual(readiness.evaluate(intent(),index=index(r),as_of=AS_OF)['status'],readiness.HOLD_PACKET)

    def test_dependency_due_holds(self):
        r=record('DEPENDENCY_DUE')
        r['operations']['valid_until']='2026-09-18T22:44:59Z'
        self.assertEqual(readiness.evaluate(intent(),index=index(r),as_of=AS_OF)['status'],readiness.HOLD_DEPENDENCY)

    def test_open_gap_holds(self):
        r=record('GAPS_OPEN')
        r['residual_gaps'].append(open_gap())
        self.assertEqual(readiness.evaluate(intent(),index=index(r),as_of=AS_OF)['status'],readiness.HOLD_GAPS)

    def test_uncertain_holds(self):
        self.assertEqual(
            readiness.evaluate(intent(),index=index(record('UNCERTAIN')),as_of=AS_OF)['status'],
            readiness.HOLD_UNCERTAIN)

    def test_mode_mismatch_holds(self):
        self.assertEqual(
            readiness.evaluate(intent('IPV6_ONLY'),index=index(record()),as_of=AS_OF)['status'],
            readiness.HOLD_SCOPE)

    def test_platform_profile_mismatch_holds(self):
        value=intent()
        value['platform_profile_ref']='controlled-platform-profile:other'
        self.assertEqual(readiness.evaluate(value,index=index(record()),as_of=AS_OF)['status'],readiness.HOLD_SCOPE)

    def test_caller_cannot_carry_production_authority(self):
        value=intent()
        value['production_authority']='APPROVED'
        with self.assertRaises(ValueError):
            readiness.evaluate(value,index=index(record()),as_of=AS_OF)

    def test_cli_can_assert_current_empty_hold(self):
        run=subprocess.run([
            sys.executable,str(ROOT/'scripts/check_address_family_readiness.py'),str(INTENT),
            '--as-of','2026-09-18T22:45:00Z',
            '--expected-status',readiness.HOLD_NONE,
        ],capture_output=True,text=True,timeout=10)
        self.assertEqual(run.returncode,0,run.stdout+run.stderr)
        self.assertEqual(json.loads(run.stdout)['status'],readiness.HOLD_NONE)


if __name__=='__main__':
    unittest.main()
