"""Clone source/result activity participates in the current port-bound campaign."""
from contextlib import redirect_stdout
from copy import deepcopy
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from lab.native_readback_fixture import Fixture
from tests.test_vmware_port_campaign import inputs as port_inputs, routes as port_routes
from tests.test_vmware_network_campaign import assets_at
from tests.test_vsphere_clone_activity import manifest as clone_manifest
from tests.test_vsphere_clone_activity_transport import routes as clone_routes
from tests.test_vsphere_task_activity import context
from tests.test_target_campaign import window
from tests.test_vsphere_observe import ref
from provisioner.execution import readback_core as c
from provisioner.execution import qualify_target as q
from provisioner.execution import recovery_review as recovery
from provisioner.execution import vsphere_task_activity as activity
from provisioner.execution.run_files import digest, encoded, write_new


def inputs(*origins):
    data = port_inputs(*origins); vm = data[1]; clone = clone_manifest(vm['origin'])
    vm.update(profile=clone['profile'], task=clone['task'])
    return data


class CloneActivityCampaignTests(unittest.TestCase):
    def test_current_campaign_collects_clone_activity_and_port_evidence_in_both_phases(self):
        with Fixture() as nf, Fixture() as vf, tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp); data = inputs(nf.origin, vf.origin); plan, vm, *_ = data
            port_routes(nf, vf, data); _, filters, methods = clone_routes(vf, vm); assets_at(folder, data, nf, vf)
            raw = encoded(plan); write_new(folder / 'plan.json', raw)
            authority = window() | dict(format='hosting-target-campaign-authority/1', plan_sha256=digest(raw), source_commit=plan['source_commit'],
                ssh_sha256=digest(Path('/usr/bin/ssh').read_bytes()), change_ref='FIXTURE', target_binding_ref='FIXTURE', isolation_ref='FIXTURE')
            write_new(folder / 'authority.json', encoded(authority)); output = folder / 'campaign'
            argv = ['qualify_target.py', str(folder / 'plan.json'), '--execute', '--authority', str(folder / 'authority.json'), '--output', str(output)]
            with patch('sys.argv', argv), patch.object(q, 'verify', return_value=dict(status='HASHES_MATCH', commit=plan['source_commit'])), \
                 patch.object(q, 'ssh_probe', return_value={'status': 'HEALTHY'}) as probe, redirect_stdout(io.StringIO()):
                self.assertEqual(q.main(), 0)
            self.assertEqual(probe.call_count, 1); self.assertFalse((output / 'ssh_key').exists())
            result = json.loads((output / 'result.json').read_bytes()); self.assertFalse(result['production_qualified'])
            for phase in ('native-before', 'native-after'):
                hashes = {k + '_sha256': digest((output / (phase + '-' + k + '.json')).read_bytes())
                          for k in ('network_before', 'portgroups_before', 'workloads', 'portgroups_after', 'network_after')}
                self.assertEqual(result[phase.replace('-', '_') + '_sha256'], digest(encoded(hashes)))
                report = json.loads((output / (phase + '-workloads.json')).read_bytes())
                self.assertEqual(report['profile'], activity.CLONE_PROFILE)
                self.assertEqual(recovery.review(vm, report, context(vm, report))['result'], 'READY_FOR_OPERATOR_RECOVERY_REVIEW')
            self.assertEqual(len(filters), 40); self.assertEqual(sum(r['path'] == methods[2] for r in vf.requests), 40)
            self.assertTrue(all(r['has_session_auth'] and not r['has_basic_auth'] for r in vf.requests))
            self.assertTrue(all(r['has_basic_auth'] and not r['has_session_auth'] for r in nf.requests))
    def test_extra_source_work_stops_collection_before_following_network_evidence(self):
        with Fixture() as nf, Fixture() as vf, tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp); data = inputs(nf.origin, vf.origin); port_routes(nf, vf, data)
            client, _, _ = clone_routes(vf, data[1]); row = deepcopy(client.activity_rows['vm-9']['completed'][0])
            row.update(key='task-99', task=ref('Task', 'task-99'), result=ref('VirtualMachine', 'vm-99'))
            client.activity_rows['vm-9']['completed'].append(row); assets_at(folder, data, nf, vf)
            assets, _, _ = q.bound_inputs(data[0], str(folder / 'known_hosts'))
            with self.assertRaises(ValueError): q.native_readback(data[0], assets, window(), folder, 'before')
            report = json.loads((folder / 'before-workloads.json').read_bytes())
            self.assertEqual(report['outcome'], 'HOLD_DIFFERENCE')
            self.assertFalse((folder / 'before-portgroups_after.json').exists())


if __name__ == '__main__': unittest.main()
