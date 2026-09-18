"""Backup protection and isolated-restore assurance tests; no native backup operation."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
import unittest

from scripts import check_backup_restore_assurance as assurance
from scripts import check_backup_restore_readiness as readiness

ROOT=Path(__file__).resolve().parents[1]
AS_OF=datetime(2026,9,18,19,0,tzinfo=timezone.utc)
INTENT=ROOT/'examples/backup_restore_readiness_intent.json.example'


def profiles():
    return {
        'consistency':'controlled-profile:consistency-fixture',
        'retention':'controlled-profile:retention-fixture',
        'location':'controlled-profile:location-fixture',
        'key':'controlled-profile:key-fixture',
        'protected_copy':'controlled-profile:protected-copy-fixture',
        'capture':'controlled-profile:capture-fixture',
        'data_path':'controlled-profile:data-path-fixture',
        'restore_target':'controlled-profile:restore-target-fixture',
        'availability_recovery':'controlled-profile:recovery-fixture'
    }


def separation():
    return {key:{
        'decision':'DENIED',
        'evidence_ref':f'controlled-evidence:{key}:fixture',
        'observed_at':'2026-09-18T17:00:00Z'
    } for key in assurance.SEPARATION_KEYS}


def record(state='CURRENT_ASSURED'):
    return {
        'assurance_id':'BACKUP-ASSURANCE-FIXTURE-01','generation':1,'state':state,
        'request_id':'EXAMPLE-SITE-CAPACITY-01',
        'wsd_engineering_ref':'docs/current/internal-hosting-solution.md',
        'backup_policy_ref':'controlled-backup-policy:fixture',
        'service_class_ref':'controlled-service-class:fixture',
        'policy_effective_at':'2026-09-17T00:00:00Z',
        'policy_review_by':'2026-12-31T23:59:59Z',
        'profiles':profiles(),
        'management_separation':separation(),
        'protected_copy':{
            'copy_ref':'controlled-copy:fixture',
            'repository_ref':'controlled-repository:fixture',
            'catalogue_ref':'controlled-catalogue:fixture',
            'key_dependency_ref':'controlled-key:fixture',
            'captured_at':'2026-09-18T16:00:00Z',
            'retention_until':'2027-01-31T00:00:00Z',
            'integrity_evidence_ref':'controlled-evidence:copy-integrity',
            'catalogue_access_evidence_ref':'controlled-evidence:catalogue-access',
            'key_access_evidence_ref':'controlled-evidence:key-access',
            'lineage_evidence_ref':'controlled-evidence:copy-lineage'
        },
        'isolated_restore':{
            'restore_ref':'controlled-restore:fixture',
            'test_set':'CT-052',
            'copy_ref':'controlled-copy:fixture',
            'isolated_target_ref':'controlled-target:isolated-fixture',
            'started_at':'2026-09-18T17:30:00Z',
            'recovered_point_at':'2026-09-18T16:55:00Z',
            'service_accepted_at':'2026-09-18T18:00:00Z',
            'evidence_valid_until':'2026-12-18T18:00:00Z',
            'consistency_evidence_ref':'controlled-evidence:consistency',
            'isolation_evidence_ref':'controlled-evidence:isolation',
            'useful_data_acceptance_ref':'controlled-evidence:data-owner-acceptance',
            'identity_key_evidence_ref':'controlled-evidence:identity-key',
            'rto_observed_seconds':'1800',
            'rpo_observed_seconds':'2100',
            'rto_profile_ref':'controlled-profile:rto',
            'rpo_profile_ref':'controlled-profile:rpo',
            'production_connection_during_restore':'DENIED'
        },
        'owners':{
            'backup_owner_role':'Fixture backup owner',
            'data_owner_role':'Fixture data owner',
            'recovery_owner_role':'Fixture recovery owner',
            'key_owner_role':'Fixture key owner'
        },
        'exclusions':['Synthetic unit-test assurance only'],
        'source_refs':[
            'docs/architecture/shared-services/5-backup-capture-independent-protection-and-isolated-restore.md',
            'docs/engineering/backup-isolated-restore-assurance.md'
        ]
    }


def index(*records):
    x=assurance.load();x['records']=list(records);return x


def intent():
    x=readiness.load(INTENT)
    x['backup_policy_ref']='controlled-backup-policy:fixture'
    x['service_class_ref']='controlled-service-class:fixture'
    p=profiles()
    x['required_profiles']={k:p[k] for k in readiness.REQUIRED_PROFILE_KEYS}
    return x


class BackupAssuranceRecordTests(unittest.TestCase):
    def test_current_index_is_valid_empty(self):
        result=assurance.validate(assurance.load(),as_of=AS_OF)
        self.assertEqual(result['record_count'],0)

    def test_current_assured_record_is_valid(self):
        result=assurance.validate(index(record()),as_of=AS_OF)
        self.assertEqual(result['current_assured_count'],1)

    def test_backup_consumer_management_access_must_be_denied(self):
        r=record();r['management_separation']['consumer_management_access']['decision']='ALLOWED'
        with self.assertRaises(ValueError):assurance.validate(index(r),as_of=AS_OF)

    def test_production_copy_delete_must_be_denied(self):
        r=record();r['management_separation']['production_copy_delete']['decision']='ALLOWED'
        with self.assertRaises(ValueError):assurance.validate(index(r),as_of=AS_OF)

    def test_production_key_destroy_must_be_denied(self):
        r=record();r['management_separation']['production_required_key_destroy']['decision']='ALLOWED'
        with self.assertRaises(ValueError):assurance.validate(index(r),as_of=AS_OF)

    def test_restore_must_use_recorded_protected_copy(self):
        r=record();r['isolated_restore']['copy_ref']='controlled-copy:other'
        with self.assertRaises(ValueError):assurance.validate(index(r),as_of=AS_OF)

    def test_restore_cannot_have_production_connection(self):
        r=record();r['isolated_restore']['production_connection_during_restore']='ALLOWED'
        with self.assertRaises(ValueError):assurance.validate(index(r),as_of=AS_OF)

    def test_restore_requires_useful_data_acceptance_reference(self):
        r=record();r['isolated_restore']['useful_data_acceptance_ref']=''
        with self.assertRaises(ValueError):assurance.validate(index(r),as_of=AS_OF)

    def test_restore_chronology_rejects_recovery_point_after_start(self):
        r=record();r['isolated_restore']['recovered_point_at']='2026-09-18T17:45:00Z'
        with self.assertRaises(ValueError):assurance.validate(index(r),as_of=AS_OF)

    def test_current_assurance_expires_when_restore_evidence_expires(self):
        r=record();r['isolated_restore']['evidence_valid_until']='2026-09-18T18:59:59Z'
        with self.assertRaises(ValueError):assurance.validate(index(r),as_of=AS_OF)

    def test_restore_due_requires_stale_evidence_or_policy(self):
        r=record('RESTORE_DUE')
        with self.assertRaises(ValueError):assurance.validate(index(r),as_of=AS_OF)
        r['isolated_restore']['evidence_valid_until']='2026-09-18T18:59:59Z'
        result=assurance.validate(index(r),as_of=AS_OF)
        self.assertEqual(result['restore_due_count'],1)

    def test_current_assurance_requires_retained_copy(self):
        r=record();r['protected_copy']['retention_until']='2026-09-18T18:59:59Z'
        with self.assertRaises(ValueError):assurance.validate(index(r),as_of=AS_OF)

    def test_duplicate_request_assurance_rejected(self):
        one=record();two=deepcopy(one);two['assurance_id']='BACKUP-ASSURANCE-FIXTURE-02'
        with self.assertRaises(ValueError):assurance.validate(index(one,two),as_of=AS_OF)

    def test_cli_empty_index_grants_no_backup_authority(self):
        run=subprocess.run([
            sys.executable,str(ROOT/'scripts/check_backup_restore_assurance.py'),
            '--as-of','2026-09-18T19:00:00Z'],
            capture_output=True,text=True,timeout=10)
        self.assertEqual(run.returncode,0,run.stdout+run.stderr)
        out=json.loads(run.stdout)
        self.assertEqual(out['record_count'],0)
        for key in ('may_access_backup_management','may_capture_backup','may_delete_copy',
                    'may_destroy_key','may_restore','may_reconnect_restored_service',
                    'may_apply','may_activate'):
            self.assertIs(out[key],False)


class BackupReadinessTests(unittest.TestCase):
    def test_current_example_holds_without_assurance(self):
        raw=readiness.load(INTENT)
        result=readiness.evaluate(raw,index=assurance.load(),as_of=AS_OF)
        self.assertEqual(result['status'],readiness.HOLD_NONE)

    def test_current_assurance_satisfies_only_readiness_prerequisite(self):
        result=readiness.evaluate(intent(),index=index(record()),as_of=AS_OF)
        self.assertEqual(result['status'],readiness.READY)
        self.assertEqual(result['assurance_id'],'BACKUP-ASSURANCE-FIXTURE-01')
        for key in ('may_access_backup_management','may_capture_backup','may_delete_copy',
                    'may_destroy_key','may_restore','may_reconnect_restored_service',
                    'may_apply','may_activate'):
            self.assertIs(result[key],False)

    def test_restore_due_holds(self):
        r=record('RESTORE_DUE');r['isolated_restore']['evidence_valid_until']='2026-09-18T18:59:59Z'
        result=readiness.evaluate(intent(),index=index(r),as_of=AS_OF)
        self.assertEqual(result['status'],readiness.HOLD_DUE)

    def test_uncertain_assurance_holds(self):
        result=readiness.evaluate(intent(),index=index(record('UNCERTAIN')),as_of=AS_OF)
        self.assertEqual(result['status'],readiness.HOLD_UNCERTAIN)

    def test_policy_mismatch_holds(self):
        i=intent();i['backup_policy_ref']='controlled-backup-policy:other'
        result=readiness.evaluate(i,index=index(record()),as_of=AS_OF)
        self.assertEqual(result['status'],readiness.HOLD_SCOPE)

    def test_service_class_mismatch_holds(self):
        i=intent();i['service_class_ref']='controlled-service-class:other'
        result=readiness.evaluate(i,index=index(record()),as_of=AS_OF)
        self.assertEqual(result['status'],readiness.HOLD_SCOPE)

    def test_profile_mismatch_holds(self):
        i=intent();i['required_profiles']['key']='controlled-profile:other-key'
        result=readiness.evaluate(i,index=index(record()),as_of=AS_OF)
        self.assertEqual(result['status'],readiness.HOLD_SCOPE)

    def test_caller_cannot_carry_production_authority(self):
        i=intent();i['production_authority']='APPROVED'
        with self.assertRaises(ValueError):readiness.evaluate(i,index=index(record()),as_of=AS_OF)

    def test_cli_can_assert_current_empty_hold(self):
        run=subprocess.run([
            sys.executable,str(ROOT/'scripts/check_backup_restore_readiness.py'),str(INTENT),
            '--as-of','2026-09-18T19:00:00Z','--expected-status',readiness.HOLD_NONE],
            capture_output=True,text=True,timeout=10)
        self.assertEqual(run.returncode,0,run.stdout+run.stderr)
        self.assertEqual(json.loads(run.stdout)['status'],readiness.HOLD_NONE)


if __name__=='__main__':unittest.main()
