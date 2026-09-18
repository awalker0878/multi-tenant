"""Native IPv6/address-family assurance tests; no native configuration mutation."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
import unittest

from scripts import check_native_ipv6_assurance as assurance
from scripts import check_native_ipv6_readiness as readiness

ROOT=Path(__file__).resolve().parents[1]
AS_OF=datetime(2026,9,18,22,5,tzinfo=timezone.utc)
INTENT=ROOT/'examples/native_ipv6_readiness_intent.json.example'


def accepted_gap():
    return {
        'gap_id':'IPV6-GAP-ACCEPTED-01',
        'status':'ACCEPTED',
        'owner_ref':'controlled-owner:ipv6-engineering',
        'treatment_ref':'controlled-treatment:ipv6-gap',
        'decision_ref':'controlled-decision:ipv6-gap-accepted',
        'review_by':'2026-12-31T23:59:59Z',
    }


def open_gap():
    return {
        'gap_id':'IPV6-GAP-OPEN-01',
        'status':'OPEN',
        'owner_ref':'controlled-owner:ipv6-engineering',
        'treatment_ref':'controlled-treatment:ipv6-gap-open',
        'decision_ref':None,
        'review_by':'2026-12-31T23:59:59Z',
    }


def record(state='CURRENT_QUALIFIED',family='IPV6_ONLY',platform='NUTANIX'):
    dual=family=='DUAL_STACK'
    return {
        'assurance_id':'NATIVE-IPV6-FIXTURE-01',
        'generation':1,
        'state':state,
        'platform':platform,
        'scope':{
            'site_ref':'controlled-site:fixture',
            'service_class_ref':'controlled-service-class:ipv6-fixture',
            'platform_profile_ref':'controlled-platform-profile:fixture',
            'security_edge_profile_ref':'controlled-security-edge-profile:fixture',
            'family_mode':family,
            'accepted_at':'2026-09-18T20:00:00Z',
            'review_by':'2026-12-31T23:59:59Z',
            'owner_ref':'controlled-owner:ipv6-engineering',
        },
        'platform_support':{
            'installed_tuple_ref':'controlled-platform-tuple:fixture',
            'api_profile_ref':'controlled-api-profile:ipv6-fixture',
            'network_backend_ref':'controlled-network-backend:fixture',
            'supported_address_mode_ref':'controlled-address-mode:ipv6',
            'endpoint_profile_ref':'controlled-endpoint-profile:ipv6',
            'management_exclusion_ref':'controlled-management-exclusion:ipv6',
        },
        'addressing':{
            'mode':'STATIC',
            'prefix_scope_ref':'controlled-prefix-scope:fixture',
            'allocation_authority_ref':'controlled-address-authority:fixture',
            'dad_ref':'controlled-ipv6-evidence:dad',
            'source_address_validation_ref':'controlled-ipv6-evidence:source-validation',
            'neighbor_discovery_ref':'controlled-ipv6-evidence:neighbor-discovery',
            'router_advertisement_ref':'controlled-ipv6-policy:router-advertisement-disabled',
            'dhcpv6_ref':'controlled-ipv6-policy:dhcpv6-not-offered',
            'redirect_policy_ref':'controlled-ipv6-policy:redirect-denied',
            'transition_mechanism_ref':'controlled-ipv6-policy:no-transition-mechanism',
        },
        'local_protocols':{
            'neighbor_solicitation_advertisement_ref':'controlled-ipv6-evidence:ns-na',
            'icmpv6_error_ref':'controlled-ipv6-evidence:icmpv6-errors',
            'packet_too_big_ref':'controlled-ipv6-evidence:packet-too-big',
            'mld_ref':'controlled-ipv6-evidence:mld',
            'fragment_policy_ref':'controlled-ipv6-policy:fragments',
            'extension_header_policy_ref':'controlled-ipv6-policy:extension-headers',
            'hop_limit_validation_ref':'controlled-ipv6-evidence:hop-limit',
        },
        'routing_security':{
            'route_authority_ref':'controlled-route-authority:ipv6',
            'forward_reply_path_ref':'controlled-path-evidence:ipv6-forward-reply',
            'same_host_distributed_ref':'controlled-path-evidence:ipv6-same-host-distributed',
            'security_outcome_parity_ref':'controlled-security-evidence:family-parity',
            'security_edge_ref':'controlled-security-edge-evidence:ipv6',
            'management_exclusion_ref':'controlled-management-evidence:ipv6-no-transit',
            'origin_specific_reply_ref':'controlled-service-route-evidence:origin-specific',
            'bypass_review_ref':'controlled-route-review:ipv6-bypass',
        },
        'mtu_pmtu':{
            'packet_frame_convention_ref':'controlled-mtu-model:packet-frame-convention',
            'workload_mtu_ref':'controlled-mtu-model:workload',
            'overlay_encapsulation_budget_ref':'controlled-mtu-model:overlay',
            'handoff_mtu_ref':'controlled-mtu-model:handoff',
            'pmtud_ref':'controlled-ipv6-evidence:pmtud',
            'ptb_blackhole_negative_ref':'controlled-ipv6-test:ptb-blackhole',
        },
        'shared_services':{
            'required_service_matrix_ref':'controlled-service-matrix:ipv6',
            'dns_aaaa_udp_tcp_ref':'controlled-service-evidence:dns-aaaa-udp-tcp',
            'identity_tls_ref':'controlled-service-evidence:tls13-ipv6',
            'time_service_ref':'controlled-service-evidence:time-ipv6',
            'telemetry_ref':'controlled-service-evidence:telemetry-ipv6',
            'artifact_repository_ref':'controlled-service-evidence:repository-ipv6',
            'protection_recovery_ref':'controlled-service-evidence:recovery-ipv6',
        },
        'failure_recovery':{
            'route_withdrawal_ref':'controlled-failure-test:route-withdrawal',
            'edge_or_link_failure_ref':'controlled-failure-test:edge-link',
            'address_dad_recovery_ref':'controlled-failure-test:address-dad-recovery',
            'survivor_capacity_ref':'controlled-capacity:ipv6-survivor',
            'recovery_service_path_ref':'controlled-recovery-path:ipv6',
            'no_ipv4_fallback_ref':None if dual else 'controlled-family-evidence:no-ipv4-fallback',
            'independent_ipv4_campaign_ref':'controlled-family-evidence:independent-ipv4' if dual else None,
        },
        'qualification':{
            'native_test_campaign_ref':'controlled-native-campaign:ipv6',
            'target_version_ref':'controlled-target-version:ipv6',
            'healthy_controls_ref':'controlled-test-evidence:healthy-controls',
            'negative_tests_ref':'controlled-test-evidence:negative-paths',
            'operational_acceptance_ref':'controlled-operational-acceptance:ipv6',
            'observed_at':'2026-09-18T21:30:00Z',
            'valid_until':'2026-12-31T23:59:59Z',
            'outcome':'PASSED_NATIVE_ADDRESS_FAMILY_QUALIFICATION',
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


def intent(family='IPV6_ONLY',platform='NUTANIX'):
    value=readiness.load(INTENT)
    value['site_ref']='controlled-site:fixture'
    value['service_class_ref']='controlled-service-class:ipv6-fixture'
    value['platform']=platform
    value['platform_profile_ref']='controlled-platform-profile:fixture'
    value['security_edge_profile_ref']='controlled-security-edge-profile:fixture'
    value['family_mode']=family
    return value


class NativeIPv6AssuranceTests(unittest.TestCase):
    def test_current_index_is_valid_empty(self):
        self.assertEqual(assurance.validate(assurance.load(),as_of=AS_OF)['record_count'],0)

    def test_current_ipv6_only_record_is_valid(self):
        self.assertEqual(assurance.validate(index(record()),as_of=AS_OF)['current_qualified_count'],1)

    def test_current_dual_stack_record_is_valid(self):
        self.assertEqual(
            assurance.validate(index(record(family='DUAL_STACK')),as_of=AS_OF)['current_qualified_count'],1)

    def test_all_native_platform_families_can_be_recorded(self):
        for platform in sorted(assurance.PLATFORMS):
            self.assertEqual(
                assurance.validate(index(record(platform=platform)),as_of=AS_OF)['current_qualified_count'],1)

    def test_ipv6_only_requires_no_ipv4_fallback_evidence(self):
        r=record()
        r['failure_recovery']['no_ipv4_fallback_ref']=None
        with self.assertRaises(ValueError):
            assurance.validate(index(r),as_of=AS_OF)

    def test_ipv6_only_rejects_dual_stack_campaign_field(self):
        r=record()
        r['failure_recovery']['independent_ipv4_campaign_ref']='controlled-family-evidence:unexpected-ipv4'
        with self.assertRaises(ValueError):
            assurance.validate(index(r),as_of=AS_OF)

    def test_dual_stack_requires_independent_ipv4_campaign(self):
        r=record(family='DUAL_STACK')
        r['failure_recovery']['independent_ipv4_campaign_ref']=None
        with self.assertRaises(ValueError):
            assurance.validate(index(r),as_of=AS_OF)

    def test_dual_stack_rejects_ipv6_only_fallback_field(self):
        r=record(family='DUAL_STACK')
        r['failure_recovery']['no_ipv4_fallback_ref']='controlled-family-evidence:wrong-mode'
        with self.assertRaises(ValueError):
            assurance.validate(index(r),as_of=AS_OF)

    def test_icmpv6_error_evidence_is_mandatory(self):
        r=record()
        r['local_protocols']['icmpv6_error_ref']=''
        with self.assertRaises(ValueError):
            assurance.validate(index(r),as_of=AS_OF)

    def test_pmtud_blackhole_negative_is_mandatory(self):
        r=record()
        r['mtu_pmtu']['ptb_blackhole_negative_ref']=''
        with self.assertRaises(ValueError):
            assurance.validate(index(r),as_of=AS_OF)

    def test_required_shared_service_matrix_is_mandatory(self):
        r=record()
        r['shared_services']['required_service_matrix_ref']=''
        with self.assertRaises(ValueError):
            assurance.validate(index(r),as_of=AS_OF)

    def test_unknown_addressing_mode_is_rejected(self):
        r=record()
        r['addressing']['mode']='MAGIC'
        with self.assertRaises(ValueError):
            assurance.validate(index(r),as_of=AS_OF)

    def test_current_qualified_requires_passing_outcome(self):
        r=record()
        r['qualification']['outcome']='FAILED_NATIVE_ADDRESS_FAMILY_QUALIFICATION'
        with self.assertRaises(ValueError):
            assurance.validate(index(r),as_of=AS_OF)

    def test_uncertain_can_represent_incomplete_qualification(self):
        r=record(state='UNCERTAIN')
        r['qualification']['outcome']='UNKNOWN_OR_INCOMPLETE'
        self.assertEqual(assurance.validate(index(r),as_of=AS_OF)['uncertain_count'],1)

    def test_qualification_must_follow_scope_acceptance(self):
        r=record()
        r['qualification']['observed_at']='2026-09-18T19:00:00Z'
        with self.assertRaises(ValueError):
            assurance.validate(index(r),as_of=AS_OF)

    def test_qualification_due_requires_expired_previous_pass(self):
        r=record(state='QUALIFICATION_DUE')
        r['qualification']['valid_until']='2026-09-18T22:04:59Z'
        self.assertEqual(assurance.validate(index(r),as_of=AS_OF)['qualification_due_count'],1)

    def test_review_due_requires_expired_scope_or_gap_review(self):
        r=record(state='REVIEW_DUE')
        r['scope']['review_by']='2026-09-18T22:04:59Z'
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

    def test_duplicate_service_scope_is_rejected(self):
        one=record()
        two=deepcopy(one)
        two['assurance_id']='NATIVE-IPV6-FIXTURE-02'
        with self.assertRaises(ValueError):
            assurance.validate(index(one,two),as_of=AS_OF)

    def test_cli_empty_index_grants_no_address_family_authority(self):
        run=subprocess.run([
            sys.executable,str(ROOT/'scripts/check_native_ipv6_assurance.py'),
            '--as-of','2026-09-18T22:05:00Z',
        ],capture_output=True,text=True,timeout=10)
        self.assertEqual(run.returncode,0,run.stdout+run.stderr)
        out=json.loads(run.stdout)
        self.assertEqual(out['record_count'],0)
        for key in (
            'may_offer_ipv6','may_change_addressing','may_change_routes',
            'may_change_security_policy','may_change_mtu','may_apply','may_activate'
        ):
            self.assertIs(out[key],False)


class NativeIPv6ReadinessTests(unittest.TestCase):
    def test_current_example_holds_without_native_ipv6_assurance(self):
        result=readiness.evaluate(readiness.load(INTENT),index=assurance.load(),as_of=AS_OF)
        self.assertEqual(result['status'],readiness.HOLD_NONE)

    def test_current_ipv6_only_is_only_readiness_prerequisite(self):
        result=readiness.evaluate(intent(),index=index(record()),as_of=AS_OF)
        self.assertEqual(result['status'],readiness.READY)
        for key in (
            'may_offer_ipv6','may_change_addressing','may_change_routes',
            'may_change_security_policy','may_change_mtu','may_apply','may_activate'
        ):
            self.assertIs(result[key],False)

    def test_current_dual_stack_scope_matches(self):
        result=readiness.evaluate(
            intent(family='DUAL_STACK'),index=index(record(family='DUAL_STACK')),as_of=AS_OF)
        self.assertEqual(result['status'],readiness.READY)

    def test_review_due_holds(self):
        r=record(state='REVIEW_DUE')
        r['scope']['review_by']='2026-09-18T22:04:59Z'
        self.assertEqual(readiness.evaluate(intent(),index=index(r),as_of=AS_OF)['status'],readiness.HOLD_REVIEW)

    def test_qualification_due_holds(self):
        r=record(state='QUALIFICATION_DUE')
        r['qualification']['valid_until']='2026-09-18T22:04:59Z'
        self.assertEqual(readiness.evaluate(intent(),index=index(r),as_of=AS_OF)['status'],readiness.HOLD_QUALIFICATION)

    def test_open_gap_holds(self):
        r=record(state='GAPS_OPEN')
        r['residual_gaps'].append(open_gap())
        self.assertEqual(readiness.evaluate(intent(),index=index(r),as_of=AS_OF)['status'],readiness.HOLD_GAPS)

    def test_uncertain_holds(self):
        r=record(state='UNCERTAIN')
        r['qualification']['outcome']='UNKNOWN_OR_INCOMPLETE'
        self.assertEqual(readiness.evaluate(intent(),index=index(r),as_of=AS_OF)['status'],readiness.HOLD_UNCERTAIN)

    def test_platform_profile_mismatch_holds(self):
        value=intent()
        value['platform_profile_ref']='controlled-platform-profile:other'
        self.assertEqual(readiness.evaluate(value,index=index(record()),as_of=AS_OF)['status'],readiness.HOLD_SCOPE)

    def test_security_edge_profile_mismatch_holds(self):
        value=intent()
        value['security_edge_profile_ref']='controlled-security-edge-profile:other'
        self.assertEqual(readiness.evaluate(value,index=index(record()),as_of=AS_OF)['status'],readiness.HOLD_SCOPE)

    def test_family_mode_mismatch_has_no_matching_record(self):
        self.assertEqual(
            readiness.evaluate(intent(family='DUAL_STACK'),index=index(record()),as_of=AS_OF)['status'],
            readiness.HOLD_NONE)

    def test_caller_cannot_carry_production_authority(self):
        value=intent()
        value['production_authority']='APPROVED'
        with self.assertRaises(ValueError):
            readiness.evaluate(value,index=index(record()),as_of=AS_OF)

    def test_cli_can_assert_current_empty_hold(self):
        run=subprocess.run([
            sys.executable,str(ROOT/'scripts/check_native_ipv6_readiness.py'),str(INTENT),
            '--as-of','2026-09-18T22:05:00Z',
            '--expected-status',readiness.HOLD_NONE,
        ],capture_output=True,text=True,timeout=10)
        self.assertEqual(run.returncode,0,run.stdout+run.stderr)
        self.assertEqual(json.loads(run.stdout)['status'],readiness.HOLD_NONE)


if __name__=='__main__':
    unittest.main()
