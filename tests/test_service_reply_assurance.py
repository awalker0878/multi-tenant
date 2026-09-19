"""Origin-specific shared-service reply assurance tests; no routing mutation."""
from __future__ import annotations
from copy import deepcopy
from datetime import datetime, timezone
import json, subprocess, sys, unittest
from pathlib import Path

from scripts import check_service_reply_assurance as assurance
from scripts import check_service_reply_readiness as readiness

ROOT=Path(__file__).resolve().parents[1]
AS_OF=datetime(2026,9,19,12,30,tzinfo=timezone.utc)
INTENT=ROOT/'examples/service_reply_readiness_intent.json.example'


def accepted_gap():
    return {
        'gap_id':'SVC-REPLY-GAP-ACCEPTED-01','status':'ACCEPTED',
        'owner_ref':'controlled-owner:service-routing',
        'treatment_ref':'controlled-treatment:service-reply',
        'decision_ref':'controlled-decision:service-reply-gap-accepted',
        'review_by':'2026-12-31T23:59:59Z'
    }


def open_gap():
    return {
        'gap_id':'SVC-REPLY-GAP-OPEN-01','status':'OPEN',
        'owner_ref':'controlled-owner:service-routing',
        'treatment_ref':'controlled-treatment:service-reply-open',
        'decision_ref':None,'review_by':'2026-12-31T23:59:59Z'
    }


def record(state='CURRENT_QUALIFIED',family='IPV6'):
    return {
      'assurance_id':'SVC-REPLY-ASSURANCE-FIXTURE-01',
      'generation':1,'state':state,'reply_id':'service-reply-fixture-01',
      'scope':{
        'site_ref':'controlled-site:fixture',
        'service_class_ref':'controlled-service-class:fixture',
        'service_binding_ref':'controlled-service-binding:fixture',
        'origin_context_ref':'controlled-origin-context:tenant01',
        'service_endpoint_ref':'controlled-service-endpoint:resolver',
        'address_family':family,
        'owner_ref':'controlled-owner:service-routing',
        'accepted_at':'2026-09-19T10:00:00Z',
        'review_by':'2026-12-31T23:59:59Z'
      },
      'binding':{
        'service_profile_ref':'controlled-service-profile:resolver',
        'endpoint_identity_ref':'controlled-service-identity:resolver',
        'authentication_ref':'controlled-service-auth:resolver',
        'entitlement_ref':'controlled-entitlement:tenant01-resolver',
        'allowed_operation_ref':'controlled-operation:dns-query',
        'management_separation_ref':'controlled-service:management-separation',
        'binding_expiry_ref':'controlled-binding:expiry',
        'revocation_test_ref':'controlled-test:binding-revocation',
        'observed_at':'2026-09-19T11:00:00Z',
        'valid_until':'2026-12-31T23:59:59Z'
      },
      'routing':{
        'forward_path_ref':'controlled-path:service-forward',
        'reply_path_ref':'controlled-path:service-reply',
        'origin_specific_return_ref':'controlled-route:origin-specific-return',
        'return_route_owner_ref':'controlled-owner:service-return-route',
        'security_edge_assurance_ref':'controlled-zip-assurance:fixture',
        'native_forwarding_ref':'controlled-forwarding:native',
        'source_validation_ref':'controlled-source-validation:service',
        'connected_route_review_ref':'controlled-route-review:connected',
        'summary_route_review_ref':'controlled-route-review:summaries',
        'nat_pbr_review_ref':'controlled-route-review:nat-pbr',
        'alternate_interface_review_ref':'controlled-route-review:alternate-interfaces',
        'no_transit_ref':'controlled-test:no-service-transit',
        'observed_at':'2026-09-19T11:05:00Z',
        'valid_until':'2026-12-31T23:59:59Z'
      },
      'failure':{
        'healthy_control_ref':'controlled-test:healthy-service-control',
        'missing_reply_route_ref':'controlled-test:missing-reply-route',
        'unavailable_next_hop_ref':'controlled-test:unavailable-next-hop',
        'edge_failure_ref':'controlled-test:service-edge-failure',
        'no_borrowed_default_ref':'controlled-test:no-borrowed-default',
        'reverse_initiation_deny_ref':'controlled-test:reverse-initiation-deny',
        'recovery_ref':'controlled-test:service-route-recovery',
        'observed_at':'2026-09-19T11:10:00Z',
        'valid_until':'2026-12-31T23:59:59Z'
      },
      'operations':{
        'availability_ref':'controlled-service:availability',
        'telemetry_ref':'controlled-service:telemetry',
        'service_loss_ref':'controlled-service:loss-behavior',
        'survivor_capacity_ref':'controlled-service:survivor-capacity',
        'version_lifecycle_ref':'controlled-service:version-lifecycle',
        'observed_at':'2026-09-19T11:15:00Z',
        'valid_until':'2026-12-31T23:59:59Z'
      },
      'residual_gaps':[accepted_gap()],
      'source_refs':[
        'docs/adr/0035-make-shared-service-replies-select-the-originating-security-context.md',
        'docs/engineering/network-boundaries/2-walk-f14-01-through-the-forward-and-reply-routes.md',
        'docs/engineering/origin-specific-service-reply-assurance.md'
      ]
    }


def index(*records):
    value=assurance.load(); value['records']=list(records); return value


def intent(family='IPV6'):
    value=readiness.load(INTENT)
    value.update({
      'reply_id':'service-reply-fixture-01',
      'site_ref':'controlled-site:fixture',
      'service_class_ref':'controlled-service-class:fixture',
      'service_binding_ref':'controlled-service-binding:fixture',
      'origin_context_ref':'controlled-origin-context:tenant01',
      'service_endpoint_ref':'controlled-service-endpoint:resolver',
      'address_family':family
    })
    return value


class ServiceReplyAssuranceTests(unittest.TestCase):
    def test_empty_index_valid(self):
        self.assertEqual(assurance.validate(assurance.load(),AS_OF)['record_count'],0)

    def test_current_ipv6_record_valid(self):
        self.assertEqual(assurance.validate(index(record()),AS_OF)['current_qualified_count'],1)

    def test_current_ipv4_record_valid(self):
        self.assertEqual(assurance.validate(index(record(family='IPV4')),AS_OF)['current_qualified_count'],1)

    def test_origin_specific_return_required(self):
        r=record(); r['routing']['origin_specific_return_ref']=''
        with self.assertRaises(ValueError): assurance.validate(index(r),AS_OF)

    def test_no_transit_evidence_required(self):
        r=record(); r['routing']['no_transit_ref']=''
        with self.assertRaises(ValueError): assurance.validate(index(r),AS_OF)

    def test_alternate_interface_review_required(self):
        r=record(); r['routing']['alternate_interface_review_ref']=''
        with self.assertRaises(ValueError): assurance.validate(index(r),AS_OF)

    def test_missing_reply_route_failure_required(self):
        r=record(); r['failure']['missing_reply_route_ref']=''
        with self.assertRaises(ValueError): assurance.validate(index(r),AS_OF)

    def test_reverse_initiation_deny_required(self):
        r=record(); r['failure']['reverse_initiation_deny_ref']=''
        with self.assertRaises(ValueError): assurance.validate(index(r),AS_OF)

    def test_binding_revocation_required(self):
        r=record(); r['binding']['revocation_test_ref']=''
        with self.assertRaises(ValueError): assurance.validate(index(r),AS_OF)

    def test_path_test_due(self):
        r=record('PATH_TEST_DUE'); r['failure']['valid_until']='2026-09-19T12:29:59Z'
        self.assertEqual(assurance.validate(index(r),AS_OF)['path_test_due_count'],1)

    def test_binding_due(self):
        r=record('BINDING_DUE'); r['binding']['valid_until']='2026-09-19T12:29:59Z'
        self.assertEqual(assurance.validate(index(r),AS_OF)['binding_due_count'],1)

    def test_current_rejects_open_gap(self):
        r=record(); r['residual_gaps'].append(open_gap())
        with self.assertRaises(ValueError): assurance.validate(index(r),AS_OF)

    def test_gaps_open(self):
        r=record('GAPS_OPEN'); r['residual_gaps'].append(open_gap())
        self.assertEqual(assurance.validate(index(r),AS_OF)['gaps_open_count'],1)

    def test_duplicate_reply_binding_rejected(self):
        one=record(); two=deepcopy(one); two['assurance_id']='SVC-REPLY-ASSURANCE-FIXTURE-02'
        with self.assertRaises(ValueError): assurance.validate(index(one,two),AS_OF)

    def test_cli_grants_no_routing_authority(self):
        run=subprocess.run([
          sys.executable,str(ROOT/'scripts/check_service_reply_assurance.py'),
          '--as-of','2026-09-19T12:30:00Z'
        ],capture_output=True,text=True,timeout=10)
        self.assertEqual(run.returncode,0,run.stdout+run.stderr)
        out=json.loads(run.stdout)
        for k in ('may_create_route','may_change_service_binding','may_change_policy',
                  'may_revoke_binding','may_change_service','may_apply','may_activate'):
            self.assertIs(out[k],False)


class ServiceReplyReadinessTests(unittest.TestCase):
    def test_empty_holds(self):
        self.assertEqual(readiness.evaluate(readiness.load(INTENT),assurance.load(),AS_OF)['status'],readiness.HOLD_NONE)

    def test_current_ready_only(self):
        result=readiness.evaluate(intent(),index(record()),AS_OF)
        self.assertEqual(result['status'],readiness.READY)
        self.assertFalse(result['may_create_route'])

    def test_path_due_holds(self):
        r=record('PATH_TEST_DUE'); r['routing']['valid_until']='2026-09-19T12:29:59Z'
        self.assertEqual(readiness.evaluate(intent(),index(r),AS_OF)['status'],readiness.HOLD_PATH)

    def test_binding_due_holds(self):
        r=record('BINDING_DUE'); r['operations']['valid_until']='2026-09-19T12:29:59Z'
        self.assertEqual(readiness.evaluate(intent(),index(r),AS_OF)['status'],readiness.HOLD_BINDING)

    def test_family_mismatch_holds(self):
        self.assertEqual(readiness.evaluate(intent('IPV4'),index(record()),AS_OF)['status'],readiness.HOLD_SCOPE)

    def test_origin_context_mismatch_holds(self):
        value=intent(); value['origin_context_ref']='controlled-origin-context:tenant02'
        self.assertEqual(readiness.evaluate(value,index(record()),AS_OF)['status'],readiness.HOLD_SCOPE)

    def test_cli_empty_hold(self):
        run=subprocess.run([
          sys.executable,str(ROOT/'scripts/check_service_reply_readiness.py'),str(INTENT),
          '--as-of','2026-09-19T12:30:00Z',
          '--expected-status',readiness.HOLD_NONE
        ],capture_output=True,text=True,timeout=10)
        self.assertEqual(run.returncode,0,run.stdout+run.stderr)


if __name__=='__main__':
    unittest.main()
