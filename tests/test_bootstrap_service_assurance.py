"""Bootstrap service assurance tests; no IPAM/DNS/bootstrap mutation."""
from __future__ import annotations
from copy import deepcopy
from datetime import datetime, timezone
import json, subprocess, sys, unittest
from pathlib import Path
from scripts import check_bootstrap_service_assurance as assurance
from scripts import check_bootstrap_service_readiness as readiness

ROOT=Path(__file__).resolve().parents[1]
AS_OF=datetime(2026,9,19,14,30,tzinfo=timezone.utc)
INTENT=ROOT/'examples/bootstrap_service_readiness_intent.json.example'

def accepted_gap():
    return {'gap_id':'BOOT-GAP-ACCEPTED-01','status':'ACCEPTED','owner_ref':'controlled-owner:bootstrap',
            'treatment_ref':'controlled-treatment:bootstrap','decision_ref':'controlled-decision:bootstrap-gap-accepted',
            'review_by':'2026-12-31T23:59:59Z'}

def open_gap():
    return {'gap_id':'BOOT-GAP-OPEN-01','status':'OPEN','owner_ref':'controlled-owner:bootstrap',
            'treatment_ref':'controlled-treatment:bootstrap-open','decision_ref':None,
            'review_by':'2026-12-31T23:59:59Z'}

def record(state='CURRENT_QUALIFIED'):
    return {
      'assurance_id':'BOOT-ASSURANCE-FIXTURE-01','generation':1,'state':state,'bootstrap_id':'bootstrap-fixture-01',
      'scope':{'site_ref':'controlled-site:fixture','service_class_ref':'controlled-service-class:fixture',
               'platform_profile_ref':'controlled-platform-profile:fixture','bootstrap_profile_ref':'controlled-bootstrap-profile:fixture',
               'address_family_profile_ref':'controlled-address-family-profile:fixture','owner_ref':'controlled-owner:bootstrap',
               'accepted_at':'2026-09-19T12:00:00Z','review_by':'2026-12-31T23:59:59Z'},
      'authoritative_lifecycle':{
        'reservation_ref':'controlled-reservation:fixture','ipam_allocation_ref':'controlled-ipam:fixture',
        'dns_registration_ref':'controlled-dns:fixture','address_assignment_method_ref':'controlled-address-assignment:fixture',
        'dhcp_metadata_profile_ref':'controlled-dhcp-metadata:fixture','address_name_reconciliation_ref':'controlled-reconcile:address-name',
        'observed_at':'2026-09-19T12:30:00Z','valid_until':'2026-12-31T23:59:59Z'},
      'minimum_dependencies':{
        'resolver_profile_ref':'controlled-service:resolver','time_profile_ref':'controlled-service:time',
        'identity_trust_ref':'controlled-trust:identity','certificate_trust_ref':'controlled-trust:certificate',
        'key_access_ref':'controlled-key-access:bootstrap','artifact_repository_ref':'controlled-service:artifact-repository',
        'telemetry_profile_ref':'controlled-service:telemetry','service_reply_assurance_ref':'controlled-service-reply:fixture',
        'observed_at':'2026-09-19T12:40:00Z','valid_until':'2026-12-31T23:59:59Z'},
      'management_execution':{
        'restricted_console_oob_ref':'controlled-management:oob','initial_privileged_trust_ref':'controlled-management:initial-trust',
        'restricted_execution_environment_ref':'controlled-execution:restricted','artifact_integrity_ref':'controlled-artifact:integrity',
        'configuration_state_recovery_ref':'controlled-recovery:config-state','management_isolation_ref':'controlled-management:isolation',
        'dependency_cut_review_ref':'controlled-review:dependency-cut',
        'observed_at':'2026-09-19T12:50:00Z','valid_until':'2026-12-31T23:59:59Z'},
      'failure_behavior':{
        'resolver_loss_ref':'controlled-failure:resolver','time_loss_ref':'controlled-failure:time',
        'repository_loss_ref':'controlled-failure:repository','telemetry_loss_ref':'controlled-failure:telemetry',
        'identity_trust_loss_ref':'controlled-failure:identity-trust',
        'no_unrestricted_fallback_ref':'controlled-failure:no-unrestricted-fallback',
        'approved_recovery_path_ref':'controlled-recovery:bootstrap',
        'observed_at':'2026-09-19T13:00:00Z','valid_until':'2026-12-31T23:59:59Z'},
      'steady_state_transition':{
        'temporary_dependency_inventory_ref':'controlled-transition:inventory',
        'steady_state_mapping_ref':'controlled-transition:mapping',
        'temporary_credential_revocation_ref':'controlled-transition:credential-revocation',
        'temporary_route_grant_cleanup_ref':'controlled-transition:route-grant-cleanup',
        'recovery_material_preservation_ref':'controlled-transition:recovery-material-preserved',
        'handover_acceptance_ref':'controlled-transition:handover-accepted',
        'observed_at':'2026-09-19T13:10:00Z','valid_until':'2026-12-31T23:59:59Z'},
      'residual_gaps':[accepted_gap()],
      'source_refs':['docs/architecture/reference/21-day-0-bootstrap-and-physical-commissioning.md',
                     'docs/architecture/shared-services/2-name-time-initialization-and-telemetry-profiles.md',
                     'docs/implementation/provisioning-strategy/2-day-0-and-steady-state-commissioning-without-circular-dependencies.md',
                     'docs/engineering/bootstrap-service-readiness-assurance.md']
    }

def index(*records):
    value=assurance.load(); value['records']=list(records); return value

def intent():
    value=readiness.load(INTENT)
    value.update({'bootstrap_id':'bootstrap-fixture-01','site_ref':'controlled-site:fixture',
                  'service_class_ref':'controlled-service-class:fixture',
                  'platform_profile_ref':'controlled-platform-profile:fixture',
                  'bootstrap_profile_ref':'controlled-bootstrap-profile:fixture',
                  'address_family_profile_ref':'controlled-address-family-profile:fixture'})
    return value

class BootstrapAssuranceTests(unittest.TestCase):
    def test_empty_index_valid(self): self.assertEqual(assurance.validate(assurance.load(),AS_OF)['record_count'],0)
    def test_current_record_valid(self): self.assertEqual(assurance.validate(index(record()),AS_OF)['current_qualified_count'],1)
    def test_authoritative_ipam_dns_required(self):
        r=record();r['authoritative_lifecycle']['ipam_allocation_ref']=''
        with self.assertRaises(ValueError): assurance.validate(index(r),AS_OF)
    def test_minimum_name_time_artifact_dependency_required(self):
        r=record();r['minimum_dependencies']['artifact_repository_ref']=''
        with self.assertRaises(ValueError): assurance.validate(index(r),AS_OF)
    def test_no_unrestricted_fallback_evidence_required(self):
        r=record();r['failure_behavior']['no_unrestricted_fallback_ref']=''
        with self.assertRaises(ValueError): assurance.validate(index(r),AS_OF)
    def test_recovery_material_preservation_required(self):
        r=record();r['steady_state_transition']['recovery_material_preservation_ref']=''
        with self.assertRaises(ValueError): assurance.validate(index(r),AS_OF)
    def test_dependency_due(self):
        r=record('DEPENDENCY_DUE');r['minimum_dependencies']['valid_until']='2026-09-19T14:29:59Z'
        self.assertEqual(assurance.validate(index(r),AS_OF)['dependency_due_count'],1)
    def test_transition_due(self):
        r=record('TRANSITION_DUE');r['steady_state_transition']['valid_until']='2026-09-19T14:29:59Z'
        self.assertEqual(assurance.validate(index(r),AS_OF)['transition_due_count'],1)
    def test_current_rejects_open_gap(self):
        r=record();r['residual_gaps'].append(open_gap())
        with self.assertRaises(ValueError): assurance.validate(index(r),AS_OF)
    def test_gaps_open(self):
        r=record('GAPS_OPEN');r['residual_gaps'].append(open_gap())
        self.assertEqual(assurance.validate(index(r),AS_OF)['gaps_open_count'],1)
    def test_duplicate_bootstrap_profile_rejected(self):
        one=record();two=deepcopy(one);two['assurance_id']='BOOT-ASSURANCE-FIXTURE-02'
        with self.assertRaises(ValueError): assurance.validate(index(one,two),AS_OF)
    def test_cli_grants_no_bootstrap_mutation_authority(self):
        run=subprocess.run([sys.executable,str(ROOT/'scripts/check_bootstrap_service_assurance.py'),'--as-of','2026-09-19T14:30:00Z'],capture_output=True,text=True,timeout=10)
        self.assertEqual(run.returncode,0,run.stdout+run.stderr);out=json.loads(run.stdout)
        for k in ('may_allocate_address','may_write_dns','may_change_dhcp_metadata','may_issue_credential','may_change_service_binding','may_retire_bootstrap_dependency','may_apply','may_activate'):
            self.assertIs(out[k],False)

class BootstrapReadinessTests(unittest.TestCase):
    def test_empty_holds(self): self.assertEqual(readiness.evaluate(readiness.load(INTENT),assurance.load(),AS_OF)['status'],readiness.HOLD_NONE)
    def test_current_ready_only(self):
        result=readiness.evaluate(intent(),index(record()),AS_OF);self.assertEqual(result['status'],readiness.READY);self.assertFalse(result['may_write_dns'])
    def test_dependency_due_holds(self):
        r=record('DEPENDENCY_DUE');r['authoritative_lifecycle']['valid_until']='2026-09-19T14:29:59Z'
        self.assertEqual(readiness.evaluate(intent(),index(r),AS_OF)['status'],readiness.HOLD_DEPENDENCY)
    def test_transition_due_holds(self):
        r=record('TRANSITION_DUE');r['failure_behavior']['valid_until']='2026-09-19T14:29:59Z'
        self.assertEqual(readiness.evaluate(intent(),index(r),AS_OF)['status'],readiness.HOLD_TRANSITION)
    def test_scope_mismatch_holds(self):
        value=intent();value['bootstrap_profile_ref']='controlled-bootstrap-profile:other'
        self.assertEqual(readiness.evaluate(value,index(record()),AS_OF)['status'],readiness.HOLD_SCOPE)
    def test_cli_empty_hold(self):
        run=subprocess.run([sys.executable,str(ROOT/'scripts/check_bootstrap_service_readiness.py'),str(INTENT),'--as-of','2026-09-19T14:30:00Z','--expected-status',readiness.HOLD_NONE],capture_output=True,text=True,timeout=10)
        self.assertEqual(run.returncode,0,run.stdout+run.stderr)

if __name__=='__main__': unittest.main()
