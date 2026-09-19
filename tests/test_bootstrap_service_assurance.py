"""Bootstrap service-initialization assurance tests; no bootstrap mutation."""
from __future__ import annotations
from copy import deepcopy
from datetime import datetime, timezone
import json, subprocess, sys, unittest
from pathlib import Path
from scripts import check_bootstrap_service_assurance as assurance
from scripts import check_bootstrap_service_readiness as readiness

ROOT=Path(__file__).resolve().parents[1]
AS_OF=datetime(2026,9,19,12,30,tzinfo=timezone.utc)
INTENT=ROOT/'examples/bootstrap_service_readiness_intent.json.example'

def accepted_gap():
    return {'gap_id':'BOOT-GAP-ACCEPTED-01','status':'ACCEPTED',
            'owner_ref':'controlled-owner:bootstrap','treatment_ref':'controlled-treatment:bootstrap',
            'decision_ref':'controlled-decision:bootstrap-gap-accepted',
            'review_by':'2026-12-31T23:59:59Z'}

def open_gap():
    return {'gap_id':'BOOT-GAP-OPEN-01','status':'OPEN',
            'owner_ref':'controlled-owner:bootstrap','treatment_ref':'controlled-treatment:bootstrap-open',
            'decision_ref':None,'review_by':'2026-12-31T23:59:59Z'}

def record(state='CURRENT_READY'):
    return {
      'assurance_id':'BOOT-ASSURANCE-FIXTURE-01','generation':1,'state':state,
      'bootstrap_id':'bootstrap-fixture-01',
      'scope':{
        'site_ref':'controlled-site:fixture',
        'service_class_ref':'controlled-service-class:fixture',
        'platform_profile_ref':'controlled-platform-profile:fixture',
        'bootstrap_profile_ref':'controlled-bootstrap-profile:fixture',
        'owner_ref':'controlled-owner:bootstrap',
        'accepted_at':'2026-09-19T10:00:00Z',
        'review_by':'2026-12-31T23:59:59Z'
      },
      'prerequisites':{
        'ipam_allocation_ref':'controlled-ipam-allocation:fixture',
        'dns_registration_ref':'controlled-dns-registration:fixture',
        'trust_assurance_ref':'controlled-trust-assurance:fixture',
        'address_family_assurance_ref':'controlled-address-family:fixture',
        'service_reply_set_ref':'controlled-service-reply-set:fixture',
        'recovery_bootstrap_ref':'controlled-recovery-bootstrap:fixture',
        'observed_at':'2026-09-19T11:00:00Z',
        'valid_until':'2026-12-31T23:59:59Z'
      },
      'initialization':{
        'address_assignment_mode_ref':'controlled-bootstrap:address-mode',
        'dhcp_metadata_scope_ref':'controlled-bootstrap:dhcp-metadata-scope',
        'resolver_profile_ref':'controlled-bootstrap:resolver',
        'time_profile_ref':'controlled-bootstrap:time',
        'artifact_repository_profile_ref':'controlled-bootstrap:artifact-repository',
        'trust_bootstrap_ref':'controlled-bootstrap:trust',
        'key_access_ref':'controlled-bootstrap:key-access',
        'initialization_network_scope_ref':'controlled-bootstrap:network-scope',
        'observed_at':'2026-09-19T11:05:00Z',
        'valid_until':'2026-12-31T23:59:59Z'
      },
      'artifact_baseline':{
        'image_baseline_ref':'controlled-image:baseline',
        'provenance_digest_ref':'controlled-image:provenance-digest',
        'support_status_ref':'controlled-image:support',
        'hardening_ref':'controlled-image:hardening',
        'vulnerability_disposition_ref':'controlled-image:vulnerability-disposition',
        'runtime_baseline_verification_ref':'controlled-image:runtime-verification',
        'retirement_rebuild_ref':'controlled-image:retirement-rebuild',
        'observed_at':'2026-09-19T11:10:00Z',
        'valid_until':'2026-12-31T23:59:59Z'
      },
      'telemetry':{
        'stable_identity_ref':'controlled-telemetry:stable-identity',
        'event_coverage_ref':'controlled-telemetry:event-coverage',
        'time_integrity_ref':'controlled-telemetry:time-integrity',
        'buffering_loss_alert_ref':'controlled-telemetry:buffering-loss-alert',
        'collection_failure_behavior_ref':'controlled-telemetry:failure-behavior',
        'observed_at':'2026-09-19T11:15:00Z',
        'valid_until':'2026-12-31T23:59:59Z'
      },
      'failure_tests':{
        'ipam_unavailable_no_guess_ref':'controlled-test:ipam-no-guess',
        'resolver_unavailable_ref':'controlled-test:resolver-unavailable',
        'time_loss_ref':'controlled-test:time-loss',
        'repository_unavailable_ref':'controlled-test:repository-unavailable',
        'collector_unavailable_ref':'controlled-test:collector-unavailable',
        'no_unrestricted_fallback_ref':'controlled-test:no-unrestricted-fallback',
        'observed_at':'2026-09-19T11:20:00Z',
        'valid_until':'2026-12-31T23:59:59Z'
      },
      'transition':{
        'temporary_dependency_register_ref':'controlled-transition:dependencies',
        'temporary_credential_ref':'controlled-transition:credentials',
        'temporary_route_ref':'controlled-transition:routes',
        'exception_register_ref':'controlled-transition:exceptions',
        'steady_state_replacement_ref':'controlled-transition:steady-state',
        'post_transfer_verification_ref':'controlled-transition:post-transfer',
        'revocation_cleanup_ref':'controlled-transition:cleanup',
        'recovery_dependency_retention_ref':'controlled-transition:recovery-retention',
        'observed_at':'2026-09-19T11:25:00Z',
        'valid_until':'2026-12-31T23:59:59Z'
      },
      'residual_gaps':[accepted_gap()],
      'source_refs':[
        'docs/architecture/shared-services/2-name-time-initialization-and-telemetry-profiles.md',
        'docs/implementation/provisioning-strategy/2-day-0-and-steady-state-commissioning-without-circular-dependencies.md',
        'docs/engineering/bootstrap-service-initialization-assurance.md'
      ]
    }

def index(*records):
    value=assurance.load(); value['records']=list(records); return value

def intent():
    value=readiness.load(INTENT)
    value.update({
      'bootstrap_id':'bootstrap-fixture-01',
      'site_ref':'controlled-site:fixture',
      'service_class_ref':'controlled-service-class:fixture',
      'platform_profile_ref':'controlled-platform-profile:fixture',
      'bootstrap_profile_ref':'controlled-bootstrap-profile:fixture'
    })
    return value

class BootstrapServiceAssuranceTests(unittest.TestCase):
    def test_empty_index_valid(self):
        self.assertEqual(assurance.validate(assurance.load(),AS_OF)['record_count'],0)

    def test_current_record_valid(self):
        self.assertEqual(assurance.validate(index(record()),AS_OF)['current_ready_count'],1)

    def test_ipam_no_guess_evidence_required(self):
        r=record(); r['failure_tests']['ipam_unavailable_no_guess_ref']=''
        with self.assertRaises(ValueError): assurance.validate(index(r),AS_OF)

    def test_no_unrestricted_fallback_required(self):
        r=record(); r['failure_tests']['no_unrestricted_fallback_ref']=''
        with self.assertRaises(ValueError): assurance.validate(index(r),AS_OF)

    def test_runtime_baseline_verification_required(self):
        r=record(); r['artifact_baseline']['runtime_baseline_verification_ref']=''
        with self.assertRaises(ValueError): assurance.validate(index(r),AS_OF)

    def test_collection_failure_behavior_required(self):
        r=record(); r['telemetry']['collection_failure_behavior_ref']=''
        with self.assertRaises(ValueError): assurance.validate(index(r),AS_OF)

    def test_recovery_dependency_retention_required(self):
        r=record(); r['transition']['recovery_dependency_retention_ref']=''
        with self.assertRaises(ValueError): assurance.validate(index(r),AS_OF)

    def test_dependency_due(self):
        r=record('DEPENDENCY_DUE'); r['initialization']['valid_until']='2026-09-19T12:29:59Z'
        self.assertEqual(assurance.validate(index(r),AS_OF)['dependency_due_count'],1)

    def test_failure_test_due(self):
        r=record('FAILURE_TEST_DUE'); r['failure_tests']['valid_until']='2026-09-19T12:29:59Z'
        self.assertEqual(assurance.validate(index(r),AS_OF)['failure_test_due_count'],1)

    def test_transition_due(self):
        r=record('TRANSITION_DUE'); r['transition']['valid_until']='2026-09-19T12:29:59Z'
        self.assertEqual(assurance.validate(index(r),AS_OF)['transition_due_count'],1)

    def test_current_rejects_open_gap(self):
        r=record(); r['residual_gaps'].append(open_gap())
        with self.assertRaises(ValueError): assurance.validate(index(r),AS_OF)

    def test_gaps_open(self):
        r=record('GAPS_OPEN'); r['residual_gaps'].append(open_gap())
        self.assertEqual(assurance.validate(index(r),AS_OF)['gaps_open_count'],1)

    def test_duplicate_bootstrap_id_rejected(self):
        one=record(); two=deepcopy(one); two['assurance_id']='BOOT-ASSURANCE-FIXTURE-02'
        with self.assertRaises(ValueError): assurance.validate(index(one,two),AS_OF)

    def test_cli_grants_no_initialization_authority(self):
        run=subprocess.run([
          sys.executable,str(ROOT/'scripts/check_bootstrap_service_assurance.py'),
          '--as-of','2026-09-19T12:30:00Z'
        ],capture_output=True,text=True,timeout=10)
        self.assertEqual(run.returncode,0,run.stdout+run.stderr)
        out=json.loads(run.stdout)
        for k in ('may_allocate_address','may_register_name','may_change_dhcp_metadata',
                  'may_change_time_source','may_issue_bootstrap_credential','may_fetch_artifact',
                  'may_change_telemetry','may_retire_temporary_dependency','may_apply','may_activate'):
            self.assertIs(out[k],False)

class BootstrapServiceReadinessTests(unittest.TestCase):
    def test_empty_holds(self):
        self.assertEqual(readiness.evaluate(readiness.load(INTENT),assurance.load(),AS_OF)['status'],readiness.HOLD_NONE)

    def test_current_ready_only(self):
        result=readiness.evaluate(intent(),index(record()),AS_OF)
        self.assertEqual(result['status'],readiness.READY)
        self.assertFalse(result['may_fetch_artifact'])

    def test_dependency_due_holds(self):
        r=record('DEPENDENCY_DUE'); r['telemetry']['valid_until']='2026-09-19T12:29:59Z'
        self.assertEqual(readiness.evaluate(intent(),index(r),AS_OF)['status'],readiness.HOLD_DEPENDENCY)

    def test_failure_due_holds(self):
        r=record('FAILURE_TEST_DUE'); r['failure_tests']['valid_until']='2026-09-19T12:29:59Z'
        self.assertEqual(readiness.evaluate(intent(),index(r),AS_OF)['status'],readiness.HOLD_FAILURE)

    def test_transition_due_holds(self):
        r=record('TRANSITION_DUE'); r['transition']['valid_until']='2026-09-19T12:29:59Z'
        self.assertEqual(readiness.evaluate(intent(),index(r),AS_OF)['status'],readiness.HOLD_TRANSITION)

    def test_scope_mismatch_holds(self):
        value=intent(); value['bootstrap_profile_ref']='controlled-bootstrap-profile:other'
        self.assertEqual(readiness.evaluate(value,index(record()),AS_OF)['status'],readiness.HOLD_SCOPE)

    def test_cli_empty_hold(self):
        run=subprocess.run([
          sys.executable,str(ROOT/'scripts/check_bootstrap_service_readiness.py'),str(INTENT),
          '--as-of','2026-09-19T12:30:00Z',
          '--expected-status',readiness.HOLD_NONE
        ],capture_output=True,text=True,timeout=10)
        self.assertEqual(run.returncode,0,run.stdout+run.stderr)

if __name__=='__main__':
    unittest.main()
