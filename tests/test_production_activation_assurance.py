"""Production activation/readiness assurance tests; no production mutation."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
import unittest

from scripts import check_production_activation_assurance as assurance
from scripts import check_production_activation_readiness as readiness

ROOT=Path(__file__).resolve().parents[1]
AS_OF=datetime(2026,9,18,22,5,tzinfo=timezone.utc)
INTENT=ROOT/'examples/production_activation_readiness_intent.json.example'


def accepted_gap():
    return {
        'gap_id':'ACT-GAP-ACCEPTED-01','status':'ACCEPTED',
        'owner_ref':'controlled-owner:service','treatment_ref':'controlled-treatment:activation',
        'decision_ref':'controlled-decision:activation-gap-accepted',
        'review_by':'2026-12-31T23:59:59Z'
    }


def open_gap():
    return {
        'gap_id':'ACT-GAP-OPEN-01','status':'OPEN',
        'owner_ref':'controlled-owner:service','treatment_ref':'controlled-treatment:activation-open',
        'decision_ref':None,'review_by':'2026-12-31T23:59:59Z'
    }


def record(state='READY_FOR_CONTROLLED_ACTIVATION',activated=False,post='NOT_RUN'):
    activation_receipt='controlled-activation-receipt:fixture' if activated else None
    activated_at='2026-09-18T21:30:00Z' if activated else None
    post_fields={
        'outcome':post,
        'live_entry_reply_ref':None,'dependency_path_ref':None,
        'monitoring_witness_ref':None,'observed_at':None,'valid_until':None
    }
    if post!='NOT_RUN':
        post_fields.update({
            'live_entry_reply_ref':'controlled-post:entry-reply',
            'dependency_path_ref':'controlled-post:dependencies',
            'monitoring_witness_ref':'controlled-post:monitoring',
            'observed_at':'2026-09-18T21:40:00Z',
            'valid_until':'2026-12-31T23:59:59Z'
        })
    return {
        'assurance_id':'ACT-ASSURANCE-FIXTURE-01','generation':1,'state':state,
        'activation_id':'activation-fixture-01',
        'scope':{
            'site_ref':'controlled-site:fixture','service_class_ref':'controlled-service-class:fixture',
            'platform_profile_ref':'controlled-platform-profile:fixture',
            'workload_scope_ref':'controlled-workload-scope:fixture',
            'exposure_profile_ref':'controlled-exposure-profile:fixture',
            'owner_ref':'controlled-owner:service','accepted_at':'2026-09-18T19:00:00Z',
            'review_by':'2026-12-31T23:59:59Z'
        },
        'prerequisites':{
            'g0_reference_adoption_ref':'controlled-gate:g0',
            'g1_site_design_ref':'controlled-gate:g1',
            'g2_platform_service_qualification_ref':'controlled-gate:g2',
            'capacity_ref':'controlled-capacity:current',
            'reservation_ref':'controlled-reservation:held',
            'address_ipam_dns_ref':'controlled-address-services:ready',
            'security_edge_ref':'controlled-security-edge:qualified',
            'control_inheritance_ref':'controlled-control-inheritance:current',
            'backup_restore_ref':'controlled-backup-restore:current',
            'native_reconciliation_ref':'controlled-native-reconciliation:current',
            'address_family_ref':'controlled-address-family:current',
            'operational_handover_ref':'controlled-operational-handover:current',
            'observed_at':'2026-09-18T20:00:00Z','valid_until':'2026-12-31T23:59:59Z'
        },
        'initial_readiness':{
            'recovery_readiness_ref':'controlled-gate:g4-recovery',
            'monitoring_alerting_ref':'controlled-gate:g4-monitoring',
            'owner_oncall_ref':'controlled-gate:g4-oncall',
            'credential_custody_ref':'controlled-gate:g4-credentials',
            'incident_containment_ref':'controlled-gate:g4-incident',
            'observed_at':'2026-09-18T20:30:00Z','valid_until':'2026-12-31T23:59:59Z'
        },
        'activation':{
            'authority_status':'APPROVED',
            'operating_authority_ref':'controlled-authority:operate',
            'decision_ref':'controlled-decision:activate',
            'authority_valid_until':'2026-12-31T23:59:59Z',
            'change_record_ref':'controlled-change:activation',
            'exposure_scope_ref':'controlled-exposure:fixture',
            'reversible_change_ref':'controlled-reversible-change:fixture',
            'pre_activation_verification_ref':'controlled-verification:pre-activation',
            'activation_receipt_ref':activation_receipt,'activated_at':activated_at
        },
        'post_activation':post_fields,
        'withdrawal':{
            'status':'REQUIRED' if post in ('FAILED','UNKNOWN') else 'TESTED_READY',
            'plan_ref':'controlled-withdrawal:plan','test_ref':'controlled-withdrawal:test',
            'preserve_data_ref':'controlled-withdrawal:preserve-data',
            'session_withdrawal_ref':'controlled-withdrawal:sessions',
            'observed_at':'2026-09-18T20:45:00Z','valid_until':'2026-12-31T23:59:59Z'
        },
        'residual_gaps':[accepted_gap()],
        'source_refs':[
            'docs/implementation/delivery-guide/7-tenant-provisioning-and-controlled-production-activation.md',
            'docs/engineering/production-activation-and-initial-readiness-assurance.md'
        ]
    }


def index(*records):
    value=assurance.load(); value['records']=list(records); return value


def intent():
    value=readiness.load(INTENT)
    value.update({
        'activation_id':'activation-fixture-01','site_ref':'controlled-site:fixture',
        'service_class_ref':'controlled-service-class:fixture',
        'platform_profile_ref':'controlled-platform-profile:fixture',
        'workload_scope_ref':'controlled-workload-scope:fixture',
        'exposure_profile_ref':'controlled-exposure-profile:fixture'
    })
    return value


class ActivationAssuranceTests(unittest.TestCase):
    def test_current_index_is_valid_empty(self):
        self.assertEqual(assurance.validate(assurance.load(),as_of=AS_OF)['record_count'],0)

    def test_ready_for_controlled_activation_is_valid(self):
        self.assertEqual(assurance.validate(index(record()),as_of=AS_OF)['ready_for_controlled_activation_count'],1)

    def test_current_activated_requires_passing_post_activation(self):
        r=record('CURRENT_ACTIVATED',activated=True,post='PASSED')
        self.assertEqual(assurance.validate(index(r),as_of=AS_OF)['current_activated_count'],1)

    def test_ready_state_cannot_claim_activation_receipt(self):
        with self.assertRaises(ValueError):
            assurance.validate(index(record(activated=True)),as_of=AS_OF)

    def test_initial_readiness_due_accepts_stale_g4(self):
        r=record('INITIAL_READINESS_DUE')
        r['initial_readiness']['valid_until']='2026-09-18T22:04:59Z'
        self.assertEqual(assurance.validate(index(r),as_of=AS_OF)['initial_readiness_due_count'],1)

    def test_expired_operating_authority_blocks_ready(self):
        r=record()
        r['activation']['authority_valid_until']='2026-09-18T22:04:59Z'
        with self.assertRaises(ValueError):
            assurance.validate(index(r),as_of=AS_OF)

    def test_post_activation_due_when_activation_has_no_live_verification(self):
        r=record('POST_ACTIVATION_DUE',activated=True,post='NOT_RUN')
        self.assertEqual(assurance.validate(index(r),as_of=AS_OF)['post_activation_due_count'],1)

    def test_failed_live_verification_requires_withdrawal(self):
        r=record('WITHDRAWAL_REQUIRED',activated=True,post='FAILED')
        self.assertEqual(assurance.validate(index(r),as_of=AS_OF)['withdrawal_required_count'],1)

    def test_failed_live_verification_cannot_be_current_activated(self):
        with self.assertRaises(ValueError):
            assurance.validate(index(record('CURRENT_ACTIVATED',activated=True,post='FAILED')),as_of=AS_OF)

    def test_post_activation_evidence_cannot_predate_activation(self):
        r=record('CURRENT_ACTIVATED',activated=True,post='PASSED')
        r['post_activation']['observed_at']='2026-09-18T21:20:00Z'
        with self.assertRaises(ValueError):
            assurance.validate(index(r),as_of=AS_OF)

    def test_gaps_open_blocks_activation(self):
        r=record('GAPS_OPEN'); r['residual_gaps'].append(open_gap())
        self.assertEqual(assurance.validate(index(r),as_of=AS_OF)['gaps_open_count'],1)

    def test_ready_state_rejects_open_gap(self):
        r=record(); r['residual_gaps'].append(open_gap())
        with self.assertRaises(ValueError):
            assurance.validate(index(r),as_of=AS_OF)

    def test_duplicate_activation_id_rejected(self):
        one=record(); two=deepcopy(one); two['assurance_id']='ACT-ASSURANCE-FIXTURE-02'
        with self.assertRaises(ValueError):
            assurance.validate(index(one,two),as_of=AS_OF)

    def test_cli_empty_index_grants_no_activation_authority(self):
        run=subprocess.run([
            sys.executable,str(ROOT/'scripts/check_production_activation_assurance.py'),
            '--as-of','2026-09-18T22:05:00Z'
        ],capture_output=True,text=True,timeout=10)
        self.assertEqual(run.returncode,0,run.stdout+run.stderr)
        out=json.loads(run.stdout); self.assertEqual(out['record_count'],0)
        for key in ('may_release_quarantine','may_change_exposure','may_activate','may_withdraw_sessions','may_apply','may_delete'):
            self.assertIs(out[key],False)


class ActivationReadinessTests(unittest.TestCase):
    def test_current_example_holds_without_assurance(self):
        self.assertEqual(readiness.evaluate(readiness.load(INTENT),index=assurance.load(),as_of=AS_OF)['status'],readiness.HOLD_NONE)

    def test_ready_record_returns_prerequisite_ready_only(self):
        result=readiness.evaluate(intent(),index=index(record()),as_of=AS_OF)
        self.assertEqual(result['status'],readiness.READY)
        self.assertFalse(result['may_activate'])

    def test_current_activated_is_distinct(self):
        result=readiness.evaluate(intent(),index=index(record('CURRENT_ACTIVATED',activated=True,post='PASSED')),as_of=AS_OF)
        self.assertEqual(result['status'],readiness.CURRENT)
        self.assertFalse(result['may_change_exposure'])

    def test_withdrawal_required_holds(self):
        r=record('WITHDRAWAL_REQUIRED',activated=True,post='UNKNOWN')
        self.assertEqual(readiness.evaluate(intent(),index=index(r),as_of=AS_OF)['status'],readiness.HOLD_WITHDRAWAL)

    def test_scope_mismatch_holds(self):
        value=intent(); value['exposure_profile_ref']='controlled-exposure-profile:other'
        self.assertEqual(readiness.evaluate(value,index=index(record()),as_of=AS_OF)['status'],readiness.HOLD_SCOPE)

    def test_caller_cannot_carry_production_authority(self):
        value=intent(); value['production_authority']='APPROVED'
        with self.assertRaises(ValueError):
            readiness.evaluate(value,index=index(record()),as_of=AS_OF)

    def test_cli_can_assert_current_empty_hold(self):
        run=subprocess.run([
            sys.executable,str(ROOT/'scripts/check_production_activation_readiness.py'),str(INTENT),
            '--as-of','2026-09-18T22:05:00Z','--expected-status',readiness.HOLD_NONE
        ],capture_output=True,text=True,timeout=10)
        self.assertEqual(run.returncode,0,run.stdout+run.stderr)
        self.assertEqual(json.loads(run.stdout)['status'],readiness.HOLD_NONE)


if __name__=='__main__': unittest.main()
