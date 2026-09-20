"""Held Flow lifecycle binding: synthetic sealed plans and loopback native evidence."""
from copy import deepcopy
from datetime import timedelta
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from lab.native_readback_fixture import Fixture
from lab.run_readback_lab import operator_context
from tests.test_flow_lifecycle import fixture as lifecycle_fixture
from tests import test_nutanix_flow_activity as fixtures
from tools import nutanix_flow_terraform_recovery as flow, terraform_recovery_review as review
from tools import nutanix_flow_activity_observe as activity, lifecycle_transition as lifecycle, readback_core as c
from tools.run_files import digest, encoded, write_new, load_private
from tools.terraform_run import select_scope


def scenario(origin, stage='bootstrap', *, expired=False):
    transition, plan = lifecycle_fixture(stage); inputs = transition['requested_inputs']
    inputs['platform_endpoint'] = transition['prior_inputs']['platform_endpoint'] = origin
    name = next(iter(inputs['members'])); native = transition['prior_outputs']['members']['value'][name]
    m = fixtures.manifest(origin); m.update(tenant_id=inputs['tenant_key'], scope_id=inputs['wsd_key'])
    r = m['resources'][0]; e = r['expected']; ident = native['quarantine_policy_id']
    r.update(ext_id=ident, category_id=native['security_category_id'], vpc_id=native['vpc_id'])
    e.update(extId=ident, name=inputs['tenant_key']+'-'+name+'-quarantine', vpcReferences=[r['vpc_id']])
    for rule in e['rules']: rule['spec']['securedGroupCategoryReferences'] = [r['category_id']]
    if stage == 'prepared': e['rules'] = e['rules'][:2]; r['services'] = {}
    m['task']['entity_ids'] = [ident]; m['task']['descendants'][0]['entity_ids'] = [ident]
    change = plan['resource_changes'][0]['change']
    for side in ('before', 'after'):
        change[side]['name'] = e['name']
        for index, rule in enumerate(change[side]['rules']): rule['ext_id'] = fixtures.uid(21+index)
    if stage == 'bootstrap':
        change['after']['rules'][2].pop('ext_id'); change['after_unknown']['rules'] = [{}, {}, {'ext_id': True}]
    start = c.timestamp(m['task']['created_after'])
    transition.update(input_sha256=digest(encoded(inputs)), valid_from=(start-timedelta(seconds=1)).isoformat(),
                      valid_until=(start+timedelta(seconds=30 if expired else 600)).isoformat())
    transition['resources'] = lifecycle.bindings(transition)
    # A real domain plan includes unchanged VPC/subnet/category resources.
    plan['resource_changes'].append(dict(address='module.owned.category', type='nutanix_category_v2', mode='managed',
        provider_name='registry.terraform.io/nutanix/nutanix', change=dict(actions=['no-op'],
        before={'id': r['category_id']}, after={'id': r['category_id']}, after_unknown={})))
    return transition, plan, m


class HeldFlowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.f = Fixture()
    @classmethod
    def tearDownClass(cls): cls.f.close()
    def setUp(self): self.setup_case()
    def setup_case(self, stage='bootstrap', *, expired=False):
        tmp = tempfile.TemporaryDirectory(); self.addCleanup(tmp.cleanup); self.base = Path(tmp.name)
        self.operation = self.base/'operation'; self.operation.mkdir(mode=0o700)
        self.ledger = self.base/'ledger'; self.ledger.mkdir(mode=0o700)
        self.transition, self.plan, self.m = scenario(self.f.origin, stage, expired=expired)
        self.inputs = self.transition['requested_inputs']; self.start = self.m['task']['created_after']
        _, scope, state_key = select_scope(review.ROOT, 'nutanix-wsd-domains', self.inputs)
        backend = dict(state_key=state_key, address='https://state.example.test/flow',
            lock_address='https://state.example.test/flow/lock', unlock_address='https://state.example.test/flow/lock',
            lock_method='POST', unlock_method='DELETE')
        self.folder = self.ledger/digest(backend['address'].encode()); self.folder.mkdir(mode=0o700)
        write_new(self.folder/'writer.lock', b'')
        values = {'inputs.json': encoded(self.inputs), 'backend.json': encoded(backend), 'plan.json': encoded(self.plan),
                  'saved.tfplan': b'FIXTURE-NOT-TERRAFORM', 'transition.json': encoded(self.transition)}
        bundle = dict(format='hosting-terraform-bundle/1', status='AWAITING_EXACT_PLAN_REVIEW', catalog_id='nutanix-wsd-domains',
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
        self.f.routes = fixtures.responses(self.m); self.f.requests = []; self.f.counts = {}; self.f.hook = None
        client = c.ReadClient(self.f.origin, self.f.origin, 'fixture', 'fixture', activity.targets(self.m), str(self.f.directory/'ca.pem'))
        report = c.observe(self.m, client, activity, interval=0); context = operator_context(self.m, report)
        context.update(accepted_plan_sha256=digest(values['saved.tfplan']), attempted_at=self.start, change_record_ref='FIXTURE-CHANGE')
        for name, value in [('manifest', self.m), ('readback', report), ('context', context)]: write_new(self.base/name, encoded(value))
    def run_review(self):
        return review.review_attempt(self.operation, self.ledger, self.base/'manifest', self.base/'readback', self.base/'context', self.base/'review')
    def bind(self, plan=None, manifest=None, transition=None):
        return flow.bind_plan(plan or self.plan, self.inputs, manifest or self.m, transition or self.transition, attempted_at=self.start)

    def test_bootstrap_and_withdrawal_preserve_every_held_ledger_byte(self):
        for stage in ('bootstrap', 'prepared'):
            self.setup_case(stage); before = {p.name: p.read_bytes() for p in self.folder.iterdir()}
            contacts = len(self.f.requests); result = self.run_review()
            self.assertEqual(result['triage']['result'], 'READY_FOR_OPERATOR_RECOVERY_REVIEW')
            self.assertEqual(result['lifecycle_sha256'], digest(encoded(self.transition)))
            self.assertEqual(set(result['plan_configuration_fields']), flow.OBSERVED_PLAN_FIELDS)
            self.assertTrue(all(result[k] is False for k in ('ledger_released', 'may_apply', 'may_delete', 'may_activate')))
            self.assertEqual(before, {p.name: p.read_bytes() for p in self.folder.iterdir()})
            self.assertEqual(len(self.f.requests), contacts); self.assertEqual((self.base/'review').stat().st_mode & 0o777, 0o600)

    def test_historical_transition_does_not_authorize_new_apply(self):
        self.setup_case(expired=True)
        with self.assertRaises(ValueError): lifecycle.validate(self.transition)
        self.assertEqual(self.run_review()['triage']['result'], 'READY_FOR_OPERATOR_RECOVERY_REVIEW')
        bad = deepcopy(self.transition); bad['valid_from'] = (c.timestamp(self.start)+timedelta(seconds=1)).isoformat()
        with self.assertRaises(ValueError): self.bind(transition=bad)

    def test_known_service_id_must_match_and_computed_new_id_needs_exact_mask(self):
        plan = deepcopy(self.plan); change = plan['resource_changes'][0]['change']
        change['after']['rules'][2]['ext_id'] = self.m['resources'][0]['expected']['rules'][2]['extId']
        change['after_unknown'] = {}; self.bind(plan=plan)
        change['after']['rules'][2]['ext_id'] = fixtures.uid(99)
        with self.assertRaises(ValueError): self.bind(plan=plan)
        plan = deepcopy(self.plan); plan['resource_changes'][0]['change']['after_unknown'] = {}
        with self.assertRaises(ValueError): self.bind(plan=plan)

    def test_retained_denies_cannot_change_identity_even_with_matching_semantics(self):
        for mutate in (lambda ch: ch['after_unknown'].update(rules=[{'ext_id': True}, {}, {'ext_id': True}]),
                       lambda ch: ch['after_unknown'].update(rules=[{}, {}, {'ext_id': 1}]),
                       lambda ch: ch['after_unknown'].update(rules=[{}, {}]),
                       lambda ch: ch['after']['rules'][0].pop('ext_id')):
            plan = deepcopy(self.plan); mutate(plan['resource_changes'][0]['change'])
            with self.assertRaises(ValueError): self.bind(plan=plan)
        plan = deepcopy(self.plan)
        for side in ('before', 'after'): plan['resource_changes'][0]['change'][side]['rules'][0]['ext_id'] = fixtures.uid(99)
        with self.assertRaises(ValueError): self.bind(plan=plan)

    def test_policy_ownership_name_or_service_intent_cannot_be_relabelled(self):
        for mutate in (lambda r: r.update(category_id=fixtures.uid(99)), lambda r: r.update(vpc_id=fixtures.uid(99)),
                       lambda r: r['expected'].update(name='foreign'),
                       lambda r: r['services']['dns'].update(port=54),
                       lambda r: r['expected']['rules'][2]['spec'].update(destAllowSpec='ALL')):
            m = deepcopy(self.m); mutate(m['resources'][0])
            with self.assertRaises(ValueError): self.bind(manifest=m)
        for field, value in [('id', fixtures.uid(99)), ('ext_id', fixtures.uid(99)), ('name', 'foreign'),
                             ('tenant_id', fixtures.uid(99)), ('is_system_defined', True)]:
            plan = deepcopy(self.plan)
            for side in ('before', 'after'): plan['resource_changes'][0]['change'][side][field] = value
            with self.assertRaises(ValueError): self.bind(plan=plan)

    def test_unresolved_replacement_adoption_or_unrelated_change_is_held(self):
        for mutate in (lambda p: p.update(resource_drift=[{}]), lambda p: p.update(complete=False),
                       lambda p: p['resource_changes'][0]['change'].update(actions=['delete', 'create']),
                       lambda p: p['resource_changes'][0]['change'].update(actions=['no-op']),
                       lambda p: p['resource_changes'][0]['change'].update(importing={'id': 'foreign'}),
                       lambda p: p['resource_changes'][0]['change']['after_unknown'].update(state=True),
                       lambda p: p['resource_changes'][0].update(provider_name='foreign'),
                       lambda p: p['resource_changes'][1]['change'].update(actions=['update']),
                       lambda p: p['resource_changes'][1]['change']['after'].update(id='foreign'),
                       lambda p: p['resource_changes'][1]['change']['after_unknown'].update(id=1)):
            plan = deepcopy(self.plan); mutate(plan)
            with self.assertRaises(ValueError): self.bind(plan=plan)

    def test_snapshot_fallback_wrong_scope_and_shifted_attempt_window_are_refused(self):
        for mutate in (lambda m: m.update(profile=fixtures.flow.PROFILE),
                       lambda m: m.update(tenant_id='foreign'), lambda m: m.update(origin='https://foreign.example.test'),
                       lambda m: m['task'].update(created_after=(c.timestamp(self.start)+timedelta(seconds=1)).isoformat())):
            m = deepcopy(self.m); mutate(m); (self.base/'manifest').write_bytes(encoded(m))
            with self.assertRaises(ValueError): self.run_review()
        self.assertFalse((self.base/'review').exists())

    def test_sealed_transition_saved_plan_and_context_cannot_be_substituted(self):
        for path in (self.operation/'transition.json', self.operation/'saved.tfplan'):
            original = path.read_bytes(); path.write_bytes(b'{}')
            with self.assertRaises(ValueError): self.run_review()
            path.write_bytes(original)
        ctx = load_private(self.base/'context'); ctx['accepted_plan_sha256'] = 'a'*64
        (self.base/'context').write_bytes(encoded(ctx))
        with self.assertRaises(ValueError): self.run_review()
        self.assertFalse((self.base/'review').exists())

    def test_unfenced_attempt_cannot_be_released(self):
        ctx = load_private(self.base/'context'); ctx['writer_fence']['state'] = 'UNKNOWN'
        (self.base/'context').write_bytes(encoded(ctx)); before = (self.folder/'head.json').read_bytes()
        self.assertEqual(self.run_review()['triage']['result'], 'HOLD_WRITER_NOT_FENCED')
        self.assertEqual((self.folder/'head.json').read_bytes(), before)

    def test_cli_reviews_offline_without_ledger_release(self):
        contacts = len(self.f.requests); args = [sys.executable, str(Path(review.__file__))]
        for key, value in dict(bundle=self.operation, ledger=self.ledger, manifest=self.base/'manifest',
                               readback=self.base/'readback', context=self.base/'context', output=self.base/'cli-review').items():
            args += ['--'+key, str(value)]
        p = subprocess.run(args, capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stdout+p.stderr); self.assertEqual(len(self.f.requests), contacts)
        self.assertFalse(load_private(self.base/'cli-review')['ledger_released'])


if __name__ == '__main__': unittest.main()
