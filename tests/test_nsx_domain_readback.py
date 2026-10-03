from copy import deepcopy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from lab.native_readback_fixture import Fixture
from lab.run_readback_lab import operator_context
from tests.nsx_domain_fixture import scenario, responses
from tests.test_nutanix_task_tree import reseal
from provisioner.execution import readback_core as c
from tools import nsx_domain_observe as domain, recovery_review as rr


class DomainReadbackTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.f = Fixture()
    @classmethod
    def tearDownClass(cls): cls.f.close()
    def setUp(self):
        _, _, self.m, _ = scenario(self.f.origin)
        self.f.routes = responses(self.m); self.f.requests = []; self.f.counts = {}; self.f.hook = None
    def observe(self):
        client = c.ReadClient(self.f.origin, self.f.origin, 'fixture', 'fixture', domain.targets(self.m), str(self.f.directory/'ca.pem'))
        return c.observe(self.m, client, domain, interval=0)

    def test_exact_four_object_coverage_is_get_only_and_replayable(self):
        report = self.observe()
        self.assertEqual(report['outcome'], 'READBACK_MATCH_NOT_QUALIFIED')
        self.assertEqual(rr.review(self.m, report, operator_context(self.m, report))['result'], 'READY_FOR_OPERATOR_RECOVERY_REVIEW')
        self.assertEqual(len(report['history'][-1]['states']), 4)
        self.assertTrue(all(request['method'] == 'GET' for request in self.f.requests))

    def test_additional_selectors_or_behavior_in_either_read_hold(self):
        for kind, mutate in [('tier1', lambda b: b.update(locale_services=[{'edge_cluster_path': '/infra/foreign'}])),
                ('segment', lambda b: b['subnets'][0].update(dhcp_config={'server_address': '192.0.2.8'})),
                ('segment', lambda b: b.update(bridge_profiles=[{'bridge_profile_path': '/infra/foreign'}])),
                ('group', lambda b: b['expression'][0].update(value='foreign')),
                ('security_policy', lambda b: b['rules'][0].update(destination_exclusions=['foreign'])),
                ('security_policy', lambda b: b.update(marked_for_delete=True))]:
            for first in (True, False):
                self.setUp(); path = '/policy/api/v1'+next(r['path'] for r in self.m['resources'] if r['kind'] == kind)
                def hook(target, count, spec):
                    if target == path and (count % 2 == 1) == first:
                        value = deepcopy(self.f.routes[target]); mutate(value['body']); return value
                    return spec
                self.f.hook = hook
                with self.subTest(kind=kind, first=first):
                    report = self.observe(); self.assertEqual(report['outcome'], 'HOLD_UNCERTAIN')
                    self.assertEqual(report['history'][-1]['states'][0]['reason'], 'NSX_DOMAIN_SHAPE_UNSUPPORTED')

    def test_metadata_is_omitted_and_inactive_provider_defaults_are_bounded(self):
        for r in self.m['resources']:
            body = self.f.routes['/policy/api/v1'+r['path']]['body']
            body.update(_last_modified_user='PRIVATE-SENTINEL', _system_owned=False, _protection='NOT_PROTECTED')
            if r['kind'] == 'segment': body.update(type='ROUTED', admin_state='UP')
            if r['kind'] == 'security_policy':
                for rule in body['rules']: rule.update(tag='', notes='', tags=[])
        report = self.observe(); self.assertEqual(report['outcome'], 'READBACK_MATCH_NOT_QUALIFIED')
        self.assertNotIn('PRIVATE-SENTINEL', json.dumps(report))

    def test_unbound_or_shared_domain_objects_are_refused_before_contact(self):
        for mutate in (lambda m: m['resources'].pop(),
                       lambda m: m['resources'][2]['expected']['expression'][0].update(paths=['/infra/segments/foreign']),
                       lambda m: m['resources'][0]['expected'].update(tier0_path='/infra/tier-0s/foreign'),
                       lambda m: m['resources'][3]['expected']['rules'][0].update(path='/infra/foreign'),
                       lambda m: m['resources'][3]['expected'].update(tags=[{'tag': 'foreign', 'scope': 'role'}])):
            m = deepcopy(self.m); mutate(m)
            with self.assertRaises(ValueError): domain.targets(m)
        self.assertEqual(self.f.requests, [])

    def test_missing_or_rehashed_shape_witness_cannot_pass_offline(self):
        report = self.observe()
        for value in (None, {'before': False, 'after': True}, {'before': 1, 'after': True}):
            bad = deepcopy(report); bad['history'][0]['states'][0]['shape_witness'] = value; reseal(bad)
            self.assertEqual(rr.review(self.m, bad, operator_context(self.m, bad))['result'], 'HOLD_INVALID_EVIDENCE')

    def test_cli_requires_explicit_contact_and_writes_private_report(self):
        with tempfile.TemporaryDirectory() as directory:
            manifest = Path(directory)/'manifest.json'; output = Path(directory)/'report.json'
            manifest.write_text(json.dumps(self.m))
            command = [sys.executable, str(Path(domain.__file__).resolve()), str(manifest)]
            result = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout+result.stderr)
            self.assertEqual(json.loads(result.stdout)['status'], 'INPUT_VALID_NO_CONTACT')
            self.assertEqual(self.f.requests, [])
            command.extend(['--read-authorized-target', '--expected-origin', self.f.origin, '--ca-file', str(self.f.directory/'ca.pem'),
                            '--output', str(output), '--interval', '0'])
            result = subprocess.run(command, capture_output=True, text=True, env=os.environ | {'NSXT_USERNAME': 'fixture', 'NSXT_PASSWORD': 'fixture'})
            self.assertEqual(result.returncode, 0, result.stdout+result.stderr)
            self.assertEqual(json.loads(result.stdout)['outcome'], 'READBACK_MATCH_NOT_QUALIFIED')
            self.assertEqual(output.stat().st_mode & 0o777, 0o600)
            self.assertNotIn(self.m['resources'][0]['path'], result.stdout)

    def test_disabled_example_validates_without_contact(self):
        path = Path(domain.__file__).resolve().parents[1]/'examples/nsx_domain_observation.json.example'
        manifest = c.load(path); domain.validate(manifest)
        self.assertFalse(manifest['contact_enabled']); self.assertTrue(manifest['origin'].endswith('.invalid'))


if __name__ == '__main__': unittest.main()
