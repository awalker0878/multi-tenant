"""Scheduling decisions and real protected descriptor bindings, without native claims."""
from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from provisioner.controlplane.authority.model import PlanScope
from provisioner.controlplane.jobs import AdmissionRefused, Job, JobRepository
from provisioner.controlplane.persistence import TenantContext, canonical_record_digest
from provisioner.controlplane.workflow.execution_selection import FileExecutionSelectionStore
from provisioner.domain.enterprise_records import plan_digest, validate_record
from provisioner.execution.run_files import encoded
from provisioner.migration.activities import FileMigrationSelectionStore
from provisioner.migration.resources import TransferLimits
from provisioner.migration.wave_schedule import (
    MemberState, SelectedWaveQualification, WaveBudget, WaveDefinition, WaveDomain,
    WaveHeld, WaveMember, _resource_keys, active_charges, candidate_decisions,
    require_wave_window)
from provisioner.qualification.action_gate import SelectedQualificationGate
from tests.provisioning.operations.campaign_fixtures import fixture
from tests.provisioning.schema.test_enterprise_records import SOURCE, TARGET, plan, workload

NOW = datetime(2026, 10, 3, tzinfo=timezone.utc)


def member(name, *, cohort='wsd-a', dependencies=(), start=None, end=None,
           runtime=600, native_suffix=None, tenant='tenant-01'):
    source = {**SOURCE, 'tenantId': tenant, 'securityDomainId': cohort}
    destination = {**TARGET, 'tenantId': tenant, 'platformFamily': 'openstack'}
    selected = plan(source=source, target=destination)
    selected['metadata']['tenantId'] = tenant
    selected['metadata']['planId'] = 'plan-' + name
    selected['spec']['workloadId'] = 'workload-' + name
    selected['spec']['route']['method'] = 'REBUILD_RESTORE'
    suffix = name if native_suffix is None else native_suffix
    for machine in selected['spec']['machineMappings']:
        machine['sourceBinding']['nativeId'] += '-' + suffix
    selected['metadata']['planDigest'] = plan_digest(selected)
    campaign = fixture()[0]
    result = WaveMember.from_plan(name, selected, campaign,
        depends_on=dependencies, window_start=start or NOW-timedelta(minutes=1),
        window_end=end or NOW+timedelta(hours=2), runtime_seconds=runtime,
        transfer_limits=TransferLimits(256, 32, 1024*1024, 64), risk_units=1)
    observed = workload()
    observed['metadata']['tenantId'] = tenant
    observed['metadata']['wsdId'] = cohort
    observed['metadata']['workloadId'] = selected['spec']['workloadId']
    for machine in observed['spec']['machines']:
        for resource in (machine, *machine['disks'], *machine['nics']):
            for history in resource['bindings']:
                history['binding']['nativeId'] += '-' + suffix
    for dataset in observed['spec']['datasets']:
        for binding in dataset['sourceBindings']:
            binding['nativeId'] += '-' + suffix
    assert not validate_record(selected, workload=observed)
    return result, observed


def domain(*members, budget=None, shared_limits=None):
    scopes = {scope: 'shared-native-hosts' for row in members for scope in (row.source, row.destination)}
    # Exact WSD grants may share a physical endpoint/scope under the same owner.
    return WaveDomain('org-01', 'tenant-01', 'domain-01', tuple(scopes.items()),
        budget or WaveBudget(8, 8, 3600*8, 8, 256*8, 32*8, 1024*1024*8),
        tuple((shared_limits or {'shared-native-hosts': 8}).items()), 'e'*64,
        NOW-timedelta(hours=1), NOW+timedelta(days=1))


def state(row, *, schedule='a'*64, status='PENDING', created=NOW,
          keys=None, job_id=None):
    return MemberState(schedule, row, status, keys or (canonical_record_digest(
        row.plan['spec']['machineMappings'][0]['sourceBinding']),),
        ('shared-native-hosts',), created, job_id)


class WaveSchedulingTests(unittest.TestCase):
    def setUp(self):
        self.a, self.observed = member('a')
        self.b, _ = member('b', dependencies=('a',))
        self.domain = domain(self.a, self.b)

    def test_deterministic_immutable_schedule_and_real_dag_validation(self):
        first = WaveDefinition('org-01', 'tenant-01', 'domain-01', self.domain.digest, (self.a, self.b))
        second = replace(first, members=(self.b, self.a))
        self.assertEqual(first.reference, second.reference)
        self.assertEqual(WaveDefinition.from_record(first.to_record()), first)
        self.assertFalse(first.run_sheet()['nativeCampaignRun'])
        self.assertEqual(first.run_sheet()['members'][0]['planDigest'], self.a.plan_digest)
        with self.assertRaisesRegex(WaveHeld, 'cycle'):
            replace(first, members=(replace(self.a, depends_on=('b',)), self.b))
        with self.assertRaisesRegex(WaveHeld, 'retained member'):
            replace(first, members=(replace(self.a, depends_on=('missing',)), self.b))
        with self.assertRaisesRegex(WaveHeld, 'repeat'):
            replace(first, members=(self.a, replace(self.a, member_id='copy')))
        changed = deepcopy(first.to_record())
        changed['members'][0]['plan']['spec']['maxDowntimeSeconds'] = 1
        with self.assertRaises(WaveHeld):
            WaveDefinition.from_record(changed)

    def test_dependencies_require_accepted_release_and_never_just_an_admitted_job(self):
        states = [state(self.a), state(self.b)]
        ready, reasons, _ = candidate_decisions(states, self.domain, NOW, None)
        self.assertEqual([row.member.member_id for row in ready], ['a'])
        self.assertEqual(reasons[states[1].key], 'DEPENDENCY_NOT_ACCEPTED')
        for status in ('ADMITTED', 'HELD'):
            waiting = [replace(states[0], status=status, job_id='original-job'), states[1]]
            self.assertEqual(candidate_decisions(waiting, self.domain, NOW, None)[0], [])
            self.assertEqual(active_charges(waiting)[0]['concurrent_jobs'], 1)
        accepted = [replace(states[0], status='SUCCEEDED', job_id='original-job'), states[1]]
        self.assertEqual([row.member.member_id for row in candidate_decisions(
            accepted, self.domain, NOW, None)[0]], ['b'])
        self.assertEqual(active_charges(accepted)[0]['concurrent_jobs'], 0)

    def test_future_window_waits_and_full_runtime_expiry_holds_without_job(self):
        future = replace(self.a, window_start=NOW+timedelta(minutes=5))
        late = replace(self.a, member_id='late', window_end=NOW+timedelta(seconds=1),
                       window_start=NOW-timedelta(hours=1))
        states = [state(future), state(late, schedule='b'*64)]
        ready, reasons, counts = candidate_decisions(states, self.domain, NOW, None)
        self.assertEqual(ready, [])
        self.assertEqual(reasons[states[0].key], 'WAITING_WINDOW')
        self.assertEqual(reasons[states[1].key], 'WINDOW_EXPIRED')
        self.assertEqual(counts['concurrent_jobs'], 0)
        with self.assertRaisesRegex(WaveHeld, 'finite window'):
            replace(self.a, runtime_seconds=1000000)
        with self.assertRaisesRegex(WaveHeld, 'UTC'):
            replace(self.a, window_start=NOW.replace(tzinfo=None))

    def test_each_exposure_downtime_risk_transfer_and_concurrency_cap_is_independent(self):
        b, _ = member('independent')
        occupied = state(self.a, status='HELD', job_id='unknown-native-start')
        candidate = state(b)
        for key, value in self.a.demand.__dict__.items():
            budget = replace(self.domain.budget, **{key: value})
            policy = replace(self.domain, budget=budget,
                             shared_risk_limits=(('shared-native-hosts', min(8, budget.risk_units)),))
            with self.subTest(cap=key):
                ready, reasons, _ = candidate_decisions([occupied, candidate], policy, NOW, None)
                self.assertEqual(ready, [])
                self.assertEqual(reasons[candidate.key], 'DOMAIN_BUDGET_UNAVAILABLE')
        narrow_risk = replace(self.domain, shared_risk_limits=(('shared-native-hosts', 1),))
        ready, reasons, _ = candidate_decisions([occupied, candidate], narrow_risk, NOW, None)
        self.assertEqual(ready, [])
        self.assertEqual(reasons[candidate.key], 'SHARED_RISK_BUDGET_UNAVAILABLE')

    def test_native_resource_overlap_is_one_charge_across_waves_and_does_not_expire(self):
        b, _ = member('other', native_suffix='a')
        occupied = state(self.a, status='HELD', job_id='original-job')
        candidate = state(b, schedule='f'*64)
        ready, reasons, totals = candidate_decisions([occupied, candidate], self.domain, NOW, None)
        self.assertEqual(ready, [])
        self.assertEqual(reasons[candidate.key], 'NATIVE_RESOURCE_OVERLAP')
        self.assertEqual(totals['risk_units'], 1)

    def test_scope_round_robin_does_not_reward_split_waves_and_skips_blocked_cohorts(self):
        a2, _ = member('a2')
        b, _ = member('other-scope', cohort='wsd-b')
        states = [state(self.a), state(a2, schedule='b'*64), state(b, schedule='c'*64)]
        policy = domain(self.a, a2, b)
        ready, _, _ = candidate_decisions(states, policy, NOW, 'wsd-a')
        self.assertEqual(ready[0].member.cohort, 'wsd-b')
        ready, _, _ = candidate_decisions(states, policy, NOW, 'wsd-b')
        self.assertEqual(ready[0].member.member_id, 'a')
        blocked_b = replace(states[2], member=replace(b, window_start=NOW+timedelta(hours=1)))
        self.assertEqual(candidate_decisions(states[:2]+[blocked_b], policy, NOW,
                                             'wsd-a')[0][0].member.cohort, 'wsd-a')
        permitted = frozenset((self.a.source, self.a.destination))
        ready, reasons, _ = candidate_decisions(states, policy, NOW, 'wsd-a', permitted_scopes=permitted)
        self.assertNotIn(states[2], ready)
        self.assertEqual(reasons[states[2].key], 'CURRENT_SCOPE_AUTHORITY_REQUIRED')

    def test_different_tenant_cannot_share_a_schedule_domain_or_verified_scope(self):
        foreign, _ = member('foreign', tenant='tenant-other')
        with self.assertRaisesRegex(WaveHeld, 'tenant authority'):
            WaveDefinition('org-01', 'tenant-01', 'domain-01', self.domain.digest, (self.a, foreign))
        with self.assertRaisesRegex(WaveHeld, 'cross tenants'):
            replace(self.domain, scopes=self.domain.scopes+((foreign.source, 'shared-native-hosts'),))
        allowed = frozenset((self.a.source, self.a.destination))
        with self.assertRaisesRegex(WaveHeld, 'exact native scopes'):
            candidate_decisions([state(foreign)], self.domain, NOW, None, permitted_scopes=allowed)

    def test_duplicate_physical_scope_unknown_budget_and_malformed_demand_are_held(self):
        relabeled = replace(self.a.source, security_domain_id='different-wsd')
        with self.assertRaisesRegex(WaveHeld, 'enroll twice'):
            replace(self.domain, scopes=self.domain.scopes+((self.a.source, 'shared-native-hosts'),))
        with self.assertRaisesRegex(WaveHeld, 'shared-risk'):
            replace(self.domain, scopes=self.domain.scopes+((relabeled, 'another-risk-owner'),))
        shared = replace(self.domain, scopes=self.domain.scopes+((relabeled, 'shared-native-hosts'),))
        self.assertEqual(shared.groups_for(replace(self.a, plan_json=self.a.plan_json)),
                         ('shared-native-hosts',))
        for policy in (replace(self.domain, expires_at=NOW),
                       replace(self.domain, observed_at=NOW+timedelta(minutes=1))):
            with self.assertRaisesRegex(WaveHeld, 'not current'):
                candidate_decisions([state(self.a)], policy, NOW, None)
        with self.assertRaisesRegex(WaveHeld, 'full approved maximum downtime'):
            replace(self.a, downtime_seconds=1)
        with self.assertRaises(WaveHeld):
            replace(self.domain.budget, concurrent_jobs=True)

    def test_overlap_inventory_derives_actual_machine_disk_nic_and_dataset_native_ids(self):
        keys = _resource_keys(self.a, self.observed)
        self.assertEqual(len(keys), 12)  # two VMs + four disks + four NICs + two datasets
        changed = deepcopy(self.observed)
        changed['spec']['machines'][0]['bindings'][0]['binding']['nativeId'] = 'a-different-vm'
        with self.assertRaisesRegex(WaveHeld, 'source workload'):
            _resource_keys(self.a, changed)
        missing = deepcopy(self.observed)
        missing['spec']['datasets'].clear()
        with self.assertRaises(WaveHeld):
            _resource_keys(self.a, missing)

    def test_delayed_start_and_every_native_effect_recheck_current_wave_window(self):
        job = Job('org-01','tenant-01','job-1','wave-member-1',self.a.plan_id,
            self.a.plan_revision,self.a.plan_digest,self.a.source,self.a.destination,
            'operator-1',('approval-1',),0,'QUEUED',1,NOW,NOW)
        valid = ('ADMITTED', self.domain.digest, self.domain.digest,
            self.domain.observed_at, self.domain.expires_at, self.a.window_start,
            self.a.window_end, self.a.runtime_seconds, job.plan_id, job.plan_revision, job.plan_digest)
        class Cursor:
            def __init__(self, row): self.row = row
            def execute(self, query, params):
                self.query, self.params = query, params
            def fetchone(self): return self.row
        require_wave_window(Cursor(valid), job, NOW, starting=True)
        require_wave_window(Cursor(None), job, NOW)  # Existing non-wave policy unchanged.
        with self.assertRaisesRegex(WaveHeld, 'persisted B09 job'):
            require_wave_window(Cursor(None), SimpleNamespace(**vars(job)), NOW)
        delayed = NOW+timedelta(hours=2)-timedelta(seconds=1)
        require_wave_window(Cursor(valid), job, delayed)
        with self.assertRaises(WaveHeld):
            require_wave_window(Cursor(valid), job, delayed, starting=True)
        for changed in (('HELD',)+valid[1:], valid[:2]+('f'*64,)+valid[3:],
                        valid[:10]+('f'*64,)):
            with self.assertRaises(WaveHeld): require_wave_window(Cursor(changed), job, NOW)
        with self.assertRaises(WaveHeld):
            require_wave_window(Cursor(valid), job, self.a.window_end)

    def test_existing_submission_checks_still_reject_invalid_inputs_before_opening_database(self):
        jobs = JobRepository(lambda: self.fail('invalid submission must not connect'),
            SimpleNamespace(revalidate_admission=lambda *args: None, revalidate_start=lambda *args: None))
        with self.assertRaises(AdmissionRefused):
            jobs.submit(TenantContext('org-01','tenant-01'), object(), idempotency_key='safe')


class WaveSelectedBindingTests(unittest.TestCase):
    def setUp(self):
        # Authentic canonical/restic fixture from the real application owner.
        from tests.test_application_migration import ApplicationMigrationTests
        self.f = ApplicationMigrationTests()
        self.f.setUp()
        self.addCleanup(self.f.doCleanups)
        self.spec, self.bundle, native_selection = fixture()
        selected = deepcopy(self.f.f.plan)
        self.artifact = {
            'format':'hosting-openstack-execution-artifact/1', 'driver':'openstack-linux-rebuild/1',
            'sourceCommit':self.spec.code_revision, 'workloadId':selected['spec']['workloadId'],
            'workloadRevision':selected['spec']['workloadRevision'], 'source':selected['spec']['source'],
            'destination':selected['spec']['destination'], 'executionScope': {
                'environment_key':'env-1','site_key':selected['spec']['destination']['locationId'],
                'platform':'openstack','tenant_key':selected['metadata']['tenantId'],
                'wsd_key':selected['spec']['destination']['securityDomainId']},
            **self.f.artifact, 'qualificationDigest':native_selection['qualificationDigest'],
            'operationsAcceptanceDigest':'1'*64, 'sourceTuple':native_selection['sourceTuple'],
            'destinationTuple':native_selection['destinationTuple'], 'guestProfile':'linux-ubuntu-2404',
            'stageBindings':{'prepare':{'kind':'terraform','parametersDigest':'2'*64,'inputDigests':{}}},
        }
        selected['spec']['route']['qualificationDigest'] = self.artifact['qualificationDigest']
        selected['spec']['execution']['artifactDigest'] = canonical_record_digest(self.artifact)
        selected['metadata']['planDigest'] = plan_digest(selected)
        self.member = WaveMember.from_plan('member', selected, self.spec,
            window_start=NOW-timedelta(minutes=1), window_end=NOW+timedelta(hours=2),
            runtime_seconds=600, transfer_limits=self.f.resources.limits, risk_units=1)
        root = self.f.f.root
        self.execution = root/'execution'; self.execution.mkdir(mode=0o700)
        self.datasets = root/'datasets'; self.datasets.mkdir(mode=0o700)
        self.cutover = root/'cutover'; self.cutover.mkdir(mode=0o700)
        self.live = root/'live'; self.live.mkdir(mode=0o700)
        self.write(self.execution/(canonical_record_digest(self.artifact)+'.json'), encoded(self.artifact))
        self.write(self.datasets/(self.f.selection.sha256+'.json'), self.f.selection.canonical)
        self.qual = SelectedWaveQualification(SelectedQualificationGate(), FileExecutionSelectionStore(self.execution),
            FileMigrationSelectionStore(dataset_directory=self.datasets, cutover_directory=self.cutover,
                                         runtime_directory=self.live))

    @staticmethod
    def write(path, value):
        path.write_bytes(value); path.chmod(0o600)

    def test_actual_approved_dataset_owner_binds_kernel_limits_and_overlap_keys(self):
        keys = self.qual.transfer_resource_keys(self.member)
        self.assertEqual(len(keys), 4)
        for dimension in ('download_kib_per_second','block_iops','stage_bytes'):
            with self.subTest(dimension=dimension):
                lower = replace(self.member.transfer_limits,
                    **{dimension:getattr(self.member.transfer_limits, dimension)-1})
                with self.assertRaisesRegex(WaveHeld, 'hard resource ceilings'):
                    self.qual.transfer_resource_keys(replace(self.member, transfer_limits=lower))

    def test_qualification_retains_original_campaign_job_without_self_reference_or_inheritance(self):
        self.assertNotEqual(self.member.plan_digest, self.spec.plan_digest)
        with patch.object(self.qual.gate, 'current_bundle', return_value=self.bundle), \
             patch.object(self.qual.gate, 'require_action') as actions:
            self.qual.require_member(None, TenantContext('org-01','tenant-01'), self.member, NOW)
        self.assertEqual(actions.call_count, 10)
        withdrawn = deepcopy(self.bundle); withdrawn['qualification']['records'].clear()
        with patch.object(self.qual.gate, 'current_bundle', return_value=withdrawn), \
             patch.object(self.qual.gate, 'require_action') as actions:
            with self.assertRaises(WaveHeld):
                self.qual.require_member(None, TenantContext('org-01','tenant-01'), self.member, NOW)
        actions.assert_not_called()

    def test_changed_selected_descriptor_raw_bytes_and_non_exact_guest_hold(self):
        path = self.datasets/(self.f.selection.sha256+'.json')
        path.write_bytes(self.f.selection.canonical+b' ')
        with self.assertRaises(ValueError): self.qual.transfer_resource_keys(self.member)
        with self.assertRaisesRegex(WaveHeld, 'qualification'):
            replace(self.member, campaign=replace(self.spec, guest_profile='LINUX'))


if __name__ == '__main__':
    unittest.main()
