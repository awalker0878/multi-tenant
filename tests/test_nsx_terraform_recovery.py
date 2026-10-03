"""Loopback NSX evidence joined to synthetic held plans; no live acceptance."""
from copy import deepcopy
from datetime import timedelta
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from lab.native_readback_fixture import Fixture
from lab.run_readback_lab import operator_context
from tests.nsx_domain_fixture import scenario, responses, uid
from tools import nsx_terraform_recovery as nsx, nsx_domain_observe as domain, terraform_recovery_review as review
from provisioner.execution import readback_core as c
from tools import lifecycle_transition as lifecycle
from provisioner.execution.run_files import digest, encoded, write_new, load_private
from tools.terraform_run import select_scope


class HeldNSXTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.f = Fixture()
    @classmethod
    def tearDownClass(cls): cls.f.close()
    def setUp(self): self.setup_case()
    def setup_case(self, stage='bootstrap', *, expired=False):
        tmp = tempfile.TemporaryDirectory(); self.addCleanup(tmp.cleanup); self.base = Path(tmp.name)
        self.operation = self.base/'operation'; self.operation.mkdir(mode=0o700)
        self.ledger = self.base/'ledger'; self.ledger.mkdir(mode=0o700)
        self.transition, self.plan, self.m, self.start = scenario(self.f.origin, stage, expired=expired)
        self.inputs = self.transition['requested_inputs']
        _, scope, state_key = select_scope(review.ROOT, 'vmware-wsd-domains', self.inputs)
        backend = dict(state_key=state_key, address='https://state.example.test/nsx',
            lock_address='https://state.example.test/nsx/lock', unlock_address='https://state.example.test/nsx/lock',
            lock_method='POST', unlock_method='DELETE')
        self.folder = self.ledger/digest(backend['address'].encode()); self.folder.mkdir(mode=0o700)
        write_new(self.folder/'writer.lock', b'')
        values = {'inputs.json': encoded(self.inputs), 'backend.json': encoded(backend), 'plan.json': encoded(self.plan),
                  'saved.tfplan': b'FIXTURE-NOT-TERRAFORM', 'transition.json': encoded(self.transition)}
        bundle = dict(format='hosting-terraform-bundle/1', status='AWAITING_EXACT_PLAN_REVIEW', catalog_id='vmware-wsd-domains',
            scope=scope, state_key=state_key, operation_id=self.m['operation_id'], generation=4,
            artifacts={k: digest(v) for k, v in values.items()})
        for name, data in values.items(): write_new(self.operation/name, data)
        write_new(self.operation/'bundle.json', encoded(bundle))
        started = dict(format='hosting-terraform-attempt/1', status='STARTED_OUTCOME_UNKNOWN', scope=scope,
            bundle_sha256=digest(encoded(bundle)), operation_id=self.m['operation_id'], generation=4,
            change_ref='FIXTURE-CHANGE', started_at=self.start)
        ident = digest(encoded({'operation': self.m['operation_id'], 'generation': 4}))
        write_new(self.folder/(ident+'.started.json'), encoded(started))
        head = started | dict(status='HOLD_RECONCILIATION_REQUIRED', stopped_at=c.now())
        write_new(self.folder/(ident+'.result.json'), encoded(head)); write_new(self.folder/'head.json', encoded(head))
        self.f.routes = responses(self.m); self.f.requests = []; self.f.counts = {}; self.f.hook = None
        client = c.ReadClient(self.f.origin, self.f.origin, 'fixture', 'fixture', domain.targets(self.m), str(self.f.directory/'ca.pem'))
        report = c.observe(self.m, client, domain, interval=0); context = operator_context(self.m, report)
        context.update(accepted_plan_sha256=digest(values['saved.tfplan']), attempted_at=self.start, change_record_ref='FIXTURE-CHANGE')
        for name, value in [('manifest', self.m), ('readback', report), ('context', context)]: write_new(self.base/name, encoded(value))
    def run_review(self, **kwargs):
        return review.review_attempt(self.operation, self.ledger, self.base/'manifest', self.base/'readback', self.base/'context', self.base/'review', **kwargs)
    def bind(self, plan=None, manifest=None, transition=None):
        return nsx.bind_plan(plan or self.plan, self.inputs, manifest or self.m, transition or self.transition, attempted_at=self.start)

    def test_bootstrap_and_withdrawal_keep_every_ledger_byte_and_make_no_contact(self):
        for stage in ('bootstrap', 'prepared'):
            self.setup_case(stage); before = {p.name: p.read_bytes() for p in self.folder.iterdir()}; count = len(self.f.requests)
            result = self.run_review()
            self.assertEqual(result['triage']['result'], 'READY_FOR_OPERATOR_RECOVERY_REVIEW')
            self.assertEqual(result['lifecycle_sha256'], digest(encoded(self.transition)))
            self.assertEqual(len(result['plan_native_bindings']), 4)
            self.assertEqual(set(result['plan_configuration_fields']), nsx.OBSERVED_PLAN_FIELDS)
            self.assertTrue(all(result[k] is False for k in ('ledger_released', 'may_apply', 'may_delete', 'may_activate')))
            self.assertEqual(before, {p.name: p.read_bytes() for p in self.folder.iterdir()})
            self.assertEqual(count, len(self.f.requests)); self.assertEqual((self.base/'review').stat().st_mode & 0o777, 0o600)

    def test_historical_window_never_authorizes_another_apply(self):
        self.setup_case(expired=True)
        with self.assertRaises(ValueError): lifecycle.validate(self.transition)
        self.assertEqual(self.run_review()['triage']['result'], 'READY_FOR_OPERATOR_RECOVERY_REVIEW')
        bad = deepcopy(self.transition); bad['valid_from'] = (c.timestamp(self.start)+timedelta(seconds=1)).isoformat()
        with self.assertRaises(ValueError): self.bind(transition=bad)

    def test_all_four_native_objects_must_be_owned_and_planned(self):
        for index in range(4):
            plan = deepcopy(self.plan); plan['resource_changes'].pop(index)
            with self.assertRaises(ValueError): self.bind(plan=plan)
            m = deepcopy(self.m); m['resources'].pop(index)
            with self.assertRaises(ValueError): self.bind(manifest=m)
            for key, value in [('id', 'foreign'), ('nsx_id', 'foreign'), ('path', '/infra/foreign'), ('display_name', 'foreign')]:
                plan = deepcopy(self.plan)
                for side in ('before', 'after'): plan['resource_changes'][index]['change'][side][key] = value
                with self.subTest(index=index, key=key), self.assertRaises(ValueError): self.bind(plan=plan)

    def test_rule_ids_and_metadata_bind_to_known_or_explicitly_computed_values(self):
        for field in ('nsx_id', 'path', 'revision', 'rule_id'):
            plan = deepcopy(self.plan); change = plan['resource_changes'][1]['change']
            change['after_unknown']['rule'][0].pop(field)
            with self.subTest(field=field), self.assertRaises(ValueError): self.bind(plan=plan)
        for mutate in (lambda ch: ch['after']['rule'][1].update(nsx_id=uid('foreign')),
                       lambda ch: ch['before']['rule'][0].update(nsx_id=uid('foreign')),
                       lambda ch: ch['after_unknown']['rule'][1].update(nsx_id=True),
                       lambda ch: ch['after_unknown']['rule'][0].update(nsx_id=1),
                       lambda ch: ch['after_unknown'].update(rule=[{}]),
                       lambda ch: ch['after_unknown']['rule'][0].update(destination_groups=True),
                       lambda ch: ch['after']['rule'][1].update(rule_id=999),
                       lambda ch: ch['after']['rule'][1].update(sequence_number=20)):
            plan = deepcopy(self.plan); mutate(plan['resource_changes'][1]['change'])
            with self.assertRaises(ValueError): self.bind(plan=plan)
        plan = deepcopy(self.plan); change = plan['resource_changes'][1]['change']; e = self.m['resources'][3]['expected']['rules'][0]
        change['after']['rule'][0].update(nsx_id=e['id'], path=e['path'], revision=e['_revision'], rule_id=e['rule_id'])
        change['after_unknown'] = {}; self.bind(plan=plan)

    def test_native_services_and_segment_allocation_cannot_be_relabelled(self):
        for mutate in (lambda m: m['resources'][1]['expected'].update(transport_zone_path='/infra/foreign'),
                       lambda m: m['resources'][1]['expected']['subnets'][0].update(gateway_address='192.0.2.9/27'),
                       lambda m: m['resources'][1]['expected']['advanced_config'].update(connectivity='OFF'),
                       lambda m: m['resources'][3]['expected'].update(locked=True),
                       lambda m: m['resources'][3]['expected']['rules'][0].update(profiles=[]),
                       lambda m: m['resources'][3]['expected']['rules'][0]['service_entries'][0].update(destination_ports=['54']),
                       lambda m: m['resources'][3]['expected']['rules'][1].update(source_groups=['192.0.2.9/32'])):
            m = deepcopy(self.m); mutate(m)
            with self.assertRaises(ValueError): self.bind(manifest=m)

    def test_unchanged_unobserved_behavior_cannot_hide_in_saved_plan(self):
        mutations = [(0, lambda d: d['subnet'][0].update(dhcp_config=[{'server_address': '192.0.2.8'}])),
                     (0, lambda d: d.update(bridge_profile=[{'path': '/infra/foreign'}])),
                     (0, lambda d: d['advanced_config'][0].update(multicast=True)),
                     (2, lambda d: d.update(edge_cluster_path='/infra/foreign')),
                     (2, lambda d: d.update(tier0_path='/infra/tier-0s/foreign')),
                     (3, lambda d: d['criteria'][0].update(condition=[{'value': 'foreign'}])),
                     (3, lambda d: d['criteria'][0]['path_expression'][0].update(unknown_selector='foreign')),
                     (1, lambda d: d.update(bridge_profile=[]))]
        for index, mutate in mutations:
            plan = deepcopy(self.plan)
            for side in ('before', 'after'): mutate(plan['resource_changes'][index]['change'][side])
            with self.subTest(index=index), self.assertRaises(ValueError): self.bind(plan=plan)

    def test_replacements_noop_lies_imports_unknowns_and_extra_resources_hold(self):
        for mutate in (lambda p: p.update(resource_drift=[{}]), lambda p: p.update(complete=False),
                       lambda p: p['resource_changes'][0]['change'].update(actions=['delete', 'create']),
                       lambda p: p['resource_changes'][0]['change'].update(actions=['no-op']),
                       lambda p: p['resource_changes'][0]['change'].update(importing={'id': 'foreign'}),
                       lambda p: p['resource_changes'][0]['change']['after_unknown'].update(revision=1),
                       lambda p: p['resource_changes'][0]['change']['after_unknown'].update(connectivity_path=True),
                       lambda p: p['resource_changes'][2]['change'].update(actions=['update']),
                       lambda p: p['resource_changes'][3].update(provider_name='foreign'),
                       lambda p: p['resource_changes'].append(deepcopy(p['resource_changes'][2]))):
            plan = deepcopy(self.plan); mutate(plan)
            with self.assertRaises(ValueError): self.bind(plan=plan)

    def test_generic_profile_foreign_origin_or_scope_and_attachment_fallback_hold(self):
        for mutate in (lambda m: m.update(profile=domain.nsx.PROFILE), lambda m: m.update(platform='vmware'),
                       lambda m: m.update(origin='https://foreign.example.test'), lambda m: m.update(scope_id='foreign')):
            m = deepcopy(self.m); mutate(m); (self.base/'manifest').write_bytes(encoded(m))
            with self.assertRaises(ValueError): self.run_review()
        (self.base/'manifest').write_bytes(encoded(self.m))
        with self.assertRaises(ValueError): self.run_review(network_manifest=self.base/'manifest', network_readback=self.base/'readback')
        self.assertFalse((self.base/'review').exists())

    def test_sealed_artifacts_and_exact_attempt_context_cannot_be_substituted(self):
        for path in (self.operation/'transition.json', self.operation/'saved.tfplan', self.operation/'plan.json'):
            original = path.read_bytes(); path.write_bytes(b'{}')
            with self.assertRaises(ValueError): self.run_review()
            path.write_bytes(original)
        context = load_private(self.base/'context'); context['accepted_plan_sha256'] = 'a'*64
        (self.base/'context').write_bytes(encoded(context))
        with self.assertRaises(ValueError): self.run_review()
        self.assertFalse((self.base/'review').exists())

    def test_fencing_quarantine_and_freshness_remain_independent_holds(self):
        original = load_private(self.base/'context')
        late = (c.timestamp(load_private(self.base/'readback')['started_at']) + timedelta(microseconds=1)).isoformat()
        for mutate, expected in [(lambda x: x.update(executor_state='UNKNOWN'), 'HOLD_WRITER_NOT_FENCED'),
                                 (lambda x: x.update(current_generation=5), 'HOLD_SUPERSEDED_CHANGE'),
                                 (lambda x: x['writer_fence'].update(state='UNVERIFIED'), 'HOLD_WRITER_NOT_FENCED'),
                                 (lambda x: x['quarantine'].update(state='UNVERIFIED'), 'HOLD_QUARANTINE_NOT_VERIFIED'),
                                 (lambda x: x['writer_fence'].update(observed_at=late), 'HOLD_WRITER_NOT_FENCED')]:
            context = deepcopy(original); mutate(context); (self.base/'context').write_bytes(encoded(context))
            result = self.run_review(); self.assertEqual(result['triage']['result'], expected)
            self.assertFalse(result['ledger_released']); (self.base/'review').unlink()

    def test_cli_writes_only_a_private_non_releasing_review_packet(self):
        args = [sys.executable, str(review.ROOT/'tools/terraform_recovery_review.py')]
        for key, value in [('bundle', self.operation), ('ledger', self.ledger), ('manifest', self.base/'manifest'),
                           ('readback', self.base/'readback'), ('context', self.base/'context'), ('output', self.base/'review')]:
            args.extend(['--'+key, str(value)])
        process = subprocess.run(args, capture_output=True, text=True)
        self.assertEqual(process.returncode, 0, process.stdout+process.stderr)
        self.assertIn('READY_FOR_OPERATOR_RECOVERY_REVIEW', process.stdout)
        self.assertNotIn(self.m['resources'][0]['path'], process.stdout)
        process = subprocess.run(args, capture_output=True, text=True)
        self.assertEqual(process.returncode, 2)


if __name__ == '__main__': unittest.main()
