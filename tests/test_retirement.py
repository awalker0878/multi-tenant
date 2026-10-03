"""Dependency-safe retirement orchestration tests; no native deletion is performed."""
from copy import deepcopy
import unittest

from provisioner.execution import readback_core as c
from tools import retirement as r


NOW = '2026-09-21T12:00:00+00:00'


def plan():
    return {
        'format': 'hosting-retirement/1',
        'source_commit': 'e030f91b59e3da0dcff2cb8d102857b11708db61',
        'operation_id': 'retire-001',
        'generation': 1,
        'scope': {
            'environment_key': 'reference',
            'site_key': 'site-01',
            'platform': 'openstack',
            'tenant_key': 'tenant-01',
            'wsd_key': 'science-prod',
        },
        'resources': [
            {'id': 'edge-01', 'kind': 'edge', 'owner': 'edge-owner', 'native_id': 'edge-native-01',
             'disposition': 'remove', 'shared': False, 'retained_data_refs': []},
            {'id': 'identity-01', 'kind': 'identity', 'owner': 'identity-owner', 'native_id': 'role-01',
             'disposition': 'deprecate', 'shared': False, 'retained_data_refs': []},
            {'id': 'data-01', 'kind': 'storage', 'owner': 'storage-owner', 'native_id': 'volume-01',
             'disposition': 'retain', 'shared': False, 'retained_data_refs': ['copy-01']},
            {'id': 'vm-01', 'kind': 'compute', 'owner': 'compute-owner', 'native_id': 'server-01',
             'disposition': 'remove', 'shared': False, 'retained_data_refs': []},
            {'id': 'dns-01', 'kind': 'dns', 'owner': 'dns-owner', 'native_id': 'dns-generation-01',
             'disposition': 'deprecate', 'shared': False, 'retained_data_refs': []},
            {'id': 'ipam-01', 'kind': 'ipam', 'owner': 'ipam-owner', 'native_id': 'allocation-01',
             'disposition': 'deprecate', 'shared': False, 'retained_data_refs': []},
            {'id': 'capacity-01', 'kind': 'capacity', 'owner': 'capacity-owner', 'native_id': 'reservation-01',
             'disposition': 'deprecate', 'shared': False, 'retained_data_refs': []},
        ],
        'retained_data': [
            {'id': 'copy-01', 'owner': 'data-owner', 'location_ref': 'vault/site-01/copy-01',
             'key_ref': 'kms/key-version-7', 'hold_ref': None, 'disposition_ref': 'RETENTION-2033',
             'final_destruction_authority_ref': 'DATA-DISPOSITION-BOARD'}
        ],
        'actions': [
            {'id': 'withdraw-edge', 'type': 'withdraw_exposure', 'needs': [], 'resources': ['edge-01']},
            {'id': 'revoke-access', 'type': 'revoke_service_access', 'needs': ['withdraw-edge'],
             'resources': ['identity-01']},
            {'id': 'protect-data', 'type': 'protect_retained_data', 'needs': ['revoke-access'],
             'resources': ['data-01']},
            {'id': 'cleanup-native', 'type': 'cleanup_native_resources', 'needs': ['protect-data'],
             'resources': ['edge-01', 'identity-01', 'vm-01']},
            {'id': 'withdraw-dns', 'type': 'withdraw_dns', 'needs': ['cleanup-native'], 'resources': ['dns-01']},
            {'id': 'retire-ipam', 'type': 'retire_ipam', 'needs': ['withdraw-dns'], 'resources': ['ipam-01']},
            {'id': 'release-ipam', 'type': 'release_ipam', 'needs': ['retire-ipam'], 'resources': ['ipam-01']},
            {'id': 'release-capacity', 'type': 'release_capacity', 'needs': ['release-ipam'],
             'resources': ['capacity-01']},
            {'id': 'close-service', 'type': 'close_service', 'needs': ['release-capacity'],
             'resources': ['capacity-01']},
        ],
    }


def evidence(value, count=None):
    rows = []
    selected = value['actions'] if count is None else value['actions'][:count]
    for action in selected:
        rows.append({
            'action_id': action['id'],
            'status': 'COMPLETED',
            'resource_ids': sorted(action['resources']),
            'observed_at': NOW,
            'evidence_ref': 'evidence/' + action['id'],
        })
    return {'format': 'hosting-retirement-evidence/1', 'plan_sha256': c.digest(value), 'receipts': rows}


class RetirementTests(unittest.TestCase):
    def test_complete_evidence_requires_external_acceptance(self):
        value = plan()
        result = r.evaluate(value, evidence(value))
        self.assertEqual(result['status'], 'RETIREMENT_EVIDENCE_COMPLETE_REQUIRES_ACCEPTANCE')
        self.assertIsNone(result['next_action'])
        self.assertFalse(result['native_acceptance'] or result['production_activation'])

    def test_partial_evidence_names_exact_next_owner(self):
        value = plan()
        result = r.evaluate(value, evidence(value, 3))
        self.assertEqual(result['status'], 'RETIREMENT_HELD_PENDING_OWNER_EVIDENCE')
        self.assertEqual(result['next_action'], 'cleanup-native')
        self.assertEqual(result['completed_actions'], ['withdraw-edge', 'revoke-access', 'protect-data'])

    def test_retained_or_transferred_resource_requires_custody_record(self):
        value = plan()
        value['resources'][2]['retained_data_refs'] = []
        with self.assertRaisesRegex(ValueError, 'retained-data custody'):
            r.validate_plan(value)

    def test_shared_resource_cannot_be_blindly_removed(self):
        value = plan()
        value['resources'][3]['shared'] = True
        with self.assertRaisesRegex(ValueError, 'Shared resources'):
            r.validate_plan(value)

    def test_ipam_retirement_must_follow_dns_withdrawal(self):
        value = plan()
        value['actions'][5]['needs'] = ['cleanup-native']
        with self.assertRaisesRegex(ValueError, 'DNS withdrawal'):
            r.validate_plan(value)

    def test_capacity_release_must_follow_all_cleanup_owners(self):
        value = plan()
        value['actions'][7]['needs'] = ['protect-data']
        with self.assertRaisesRegex(ValueError, 'all applicable cleanup owners'):
            r.validate_plan(value)

    def test_address_release_requires_an_accountable_owner_action(self):
        value = plan()
        value['actions'].pop(6)
        value['actions'][6]['needs'] = ['retire-ipam']
        with self.assertRaisesRegex(ValueError, 'accountable owner action'):
            r.validate_plan(value)

    def test_address_release_must_follow_observed_retirement(self):
        value = plan()
        value['actions'][6]['needs'] = ['withdraw-dns']
        with self.assertRaisesRegex(ValueError, 'observed IPAM retirement'):
            r.validate_plan(value)

    def test_capacity_release_must_follow_address_release(self):
        value = plan()
        value['actions'][7]['needs'] = ['retire-ipam']
        value['actions'][8]['needs'] = ['release-capacity', 'release-ipam']
        with self.assertRaisesRegex(ValueError, 'all applicable cleanup owners'):
            r.validate_plan(value)

    def test_service_closure_must_cover_every_prior_action(self):
        value = plan()
        value['actions'][8]['needs'] = ['protect-data']
        with self.assertRaisesRegex(ValueError, 'every prior retirement action'):
            r.validate_plan(value)

    def test_evidence_cannot_skip_a_dependency(self):
        value = plan()
        rows = evidence(value)['receipts']
        rows.pop(2)
        bad = {'format': 'hosting-retirement-evidence/1', 'plan_sha256': c.digest(value), 'receipts': rows}
        with self.assertRaisesRegex(ValueError, 'dependency order'):
            r.validate_evidence(value, bad)

    def test_evidence_resource_set_is_exact(self):
        value = plan()
        bad = evidence(value, 1)
        bad['receipts'][0]['resource_ids'] = ['vm-01']
        with self.assertRaisesRegex(ValueError, 'resource set differs'):
            r.validate_evidence(value, bad)

    def test_foreign_evidence_cannot_authorize_retirement(self):
        value = plan()
        bad = evidence(value, 1)
        bad['plan_sha256'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'another plan'):
            r.validate_evidence(value, bad)

    def test_removed_resource_must_have_accountable_owner_action(self):
        value = plan()
        value['actions'][3]['resources'].remove('vm-01')
        with self.assertRaisesRegex(ValueError, 'no accountable retirement owner action'):
            r.validate_plan(value)


if __name__ == '__main__':
    unittest.main()
