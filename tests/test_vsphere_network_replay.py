"""Offline network review recomputes native witnesses, not just report hashes."""
from copy import deepcopy
from datetime import datetime, timezone
import unittest
from tests import test_vsphere_network_observe as groups, test_vsphere_port_observe as ports
from provisioner.execution import readback_core as c
from tools import recovery_review as review


def reseal(report):
    for row in report['history']: row['snapshot_sha256'] = c.digest(row['states'])
    report['content_sha256'] = c.digest({k: v for k, v in report.items() if k != 'content_sha256'})


class NetworkReplayTests(unittest.TestCase):
    def test_both_profiles_recompute_complete_selected_witnesses(self):
        for fixture, adapter in ((groups, groups.n), (ports, ports.p)):
            manifest = fixture.manifest(); report = c.observe(manifest, fixture.Client(manifest), adapter, interval=0)
            self.assertEqual(review.check_report(manifest, report, datetime.now(timezone.utc), 300, adapter=adapter),
                             'READBACK_MATCH_NOT_QUALIFIED')

    def test_rehashed_forged_group_or_port_facts_cannot_keep_a_match(self):
        m = ports.manifest(); original = c.observe(m, ports.Client(m), ports.p, interval=0)
        changes = [lambda s: s['attachment_witness']['after']['17'].update(connectionCookie=99),
            lambda s: s['attachment_witness']['before']['17']['connectee'].update(nicKey='4001'),
            lambda s: s['attachment_witness']['after']['17']['proxyHost'].update(value='host-2'),
            lambda s: s['attachment_witness']['portgroup']['after']['config'].update(key='foreign'),
            lambda s: s['attachment_witness']['portgroup']['before']['switch'].update(uuid='foreign'),
            lambda s: s['attachment_witness']['after'].clear(), lambda s: s.pop('attachment_witness'),
            lambda s: s.update(task_completion_observed=True), lambda s: s.update(config_sha256='f' * 64)]
        for change in changes:
            report = deepcopy(original)
            for row in report['history']: change(row['states'][0])
            reseal(report)
            with self.assertRaises(ValueError): review.check_report(m, report, datetime.now(timezone.utc), 300, adapter=ports.p)

    def test_rehashed_group_snapshot_or_missing_witness_cannot_keep_a_match(self):
        m = groups.manifest(); original = c.observe(m, groups.Client(m), groups.n, interval=0)
        for change in (lambda s: s['group_witness']['after']['config'].update(configVersion='99'),
                       lambda s: s['group_witness']['before']['switch'].clear(), lambda s: s.pop('group_witness')):
            report = deepcopy(original)
            for row in report['history']: change(row['states'][0])
            reseal(report)
            with self.assertRaises(ValueError): review.check_report(m, report, datetime.now(timezone.utc), 300, adapter=groups.n)

    def test_incomplete_native_ports_remain_replayable_unknown_not_success(self):
        m = ports.manifest(); client = ports.Client(m); client.rows['dvportgroup-1'] = []
        report = c.observe(m, client, ports.p, interval=0)
        self.assertEqual(review.check_report(m, report, datetime.now(timezone.utc), 300, adapter=ports.p), 'HOLD_UNCERTAIN')
        report['history'][0]['states'][0]['progress'] = 'COMPLETE'; reseal(report)
        with self.assertRaises(ValueError): review.check_report(m, report, datetime.now(timezone.utc), 300, adapter=ports.p)

    def test_recovery_dispatch_does_not_treat_network_snapshot_as_task_completion(self):
        m = ports.manifest()
        with self.assertRaises(ValueError): review.adapter_for(m).validate(m)


if __name__ == '__main__': unittest.main()
