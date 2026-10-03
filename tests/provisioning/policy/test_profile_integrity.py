"""Requirements and limitations cannot disappear at the profile boundary."""
from dataclasses import replace
import json
from pathlib import Path
import tempfile
import unittest

from provisioner.domain.errors import ProvisioningError
from provisioner.execution.plan import create_plan
from provisioner.inventory import model
from provisioner.profiles import loader
from tests.provisioning import support
from tests.provisioning.policy.test_profile_versions import edited_catalogs, _edit


class ProfileIntegrityTests(unittest.TestCase):
    def test_unknown_in_memory_status_is_not_implemented(self):
        profile = support.catalogs().get('compute', 'medium')
        self.assertFalse(replace(profile, status='FUTURE_UNREVIEWED').implemented)

    def test_selected_limits_are_complete_and_deterministic(self):
        catalog = support.catalogs()
        resolution = support.reference_plan('recovery-enabled').resolution
        expected = set()
        for family, names in resolution.profiles.items():
            if family == 'services':
                for name in names.values():
                    expected.update(catalog.get('service', name).limits)
            elif names is not None:
                expected.update(catalog.get(family, names).limits)
        self.assertEqual(set(resolution.limits), expected)
        self.assertEqual(len(resolution.limits), len(expected))
        self.assertEqual(resolution.limits,
                         support.reference_plan('recovery-enabled').resolution.limits)

    def test_malformed_capability_lists_are_not_coerced(self):
        for value in ['ipv4', {'ipv4': True}, ['vm_create', 'vm_create'],
                      ['unknown_vendor_feature'], [None], None]:
            with self.subTest(value=value), self.assertRaises(ProvisioningError):
                edited_catalogs(lambda root: _edit(root / 'compute/catalog.json',
                    lambda d: d['profiles'][0]['requires'].__setitem__('capabilities', value)))

    def test_malformed_identity_requirements_inputs_and_limits_are_refused(self):
        for field, value in [('rank', True), ('rank', 0), ('profile', None),
                             ('requires', []), ('platform_inputs', []),
                             ('limits', 'hidden warning'), ('limits', [None]),
                             ('description', ''), ('version', '1\n')]:
            with self.subTest(field=field, value=value), self.assertRaises(ProvisioningError):
                edited_catalogs(lambda root: _edit(root / 'compute/catalog.json',
                    lambda d: d['profiles'][0].__setitem__(field, value)))

    def test_parser_rejects_duplicate_properties_and_nonfinite_values(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'compute/catalog.json'
            path.parent.mkdir()
            for raw in ['{"family":"compute","family":"storage"}',
                        '{"family":"compute","rank":NaN}', ' ' * (1024 * 1024 + 1)]:
                path.write_text(raw)
                with self.assertRaises(ProvisioningError):
                    loader._load_one(path)

    def test_profile_requirements_include_compute_storage_and_service_effects(self):
        resolution = support.reference_plan('storage-heavy').resolution
        self.assertTrue({'vm_create', 'cpu_topology', 'boot_volume', 'data_volumes',
                         'disk_order', 'storage_placement', 'dns_registration',
                         'identity_join', 'time_sync', 'log_forwarding',
                         'backup_restore'} <= set(resolution.required_capabilities))

    def test_missing_compute_capability_blocks_even_a_network_capable_fixture(self):
        source = Path(model.__file__).parent / 'fixtures/openstack-reference.json'
        document = json.loads(source.read_text())
        for site in document['sites']:
            for cell in site['cells']:
                cell['capabilities'].remove('vm_create')
        inventory = model.build(document)
        with self.assertRaises(ProvisioningError) as caught:
            create_plan(support.reference_document(), '<test>', inventory, support.catalogs())
        self.assertEqual(caught.exception.code, 'NO_ELIGIBLE_PLACEMENT')

    def test_new_requirements_never_authorize_fixture_plans(self):
        for platform in support.PLATFORMS:
            plan = support.platform_plan(platform)
            self.assertIs(plan.native_contact, False)
            self.assertFalse(plan.decision.authorized)
            self.assertEqual(plan.status, 'PLANNED_DISABLED_NOT_AUTHORIZED')


if __name__ == '__main__':
    unittest.main()
