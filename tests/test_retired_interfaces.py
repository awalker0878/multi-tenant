"""Protect the exact retirement contract, including package-owned qualification."""
from __future__ import annotations

import ast
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import check_retired_interfaces as retirement

ROOT = Path(__file__).resolve().parents[1]
EXPECTED = {
    'tools/flow_policy.py': ('path', 'provisioner/execution/flow_policy.py'),
    'tools/lifecycle_transition.py': ('path', 'provisioner/execution/lifecycle_transition.py'),
    'tools/openstack_transition.py': ('path', 'provisioner/execution/openstack_transition.py'),
    'tools/plan_review.py': ('path', 'provisioner/execution/plan_review.py'),
    'tools/terraform_apply.py': ('path', 'provisioner/execution/terraform_apply.py'),
    'tools/terraform_run.py': ('path', 'provisioner/execution/terraform_run.py'),
    'tools/wsd_handoff.py': ('path', 'provisioner/execution/wsd_handoff.py'),

    'tools/neutron_observe.py': ('path', 'provisioner/execution/neutron_observe.py'),
    'tools/readback_core.py': ('path', 'provisioner/execution/readback_core.py'),
    'tools/route_record_review.py': ('path', 'provisioner/execution/route_record_review.py'),
    'tools/run_files.py': ('path', 'provisioner/execution/run_files.py'),

    'tools/input_review.py': ('path', 'provisioner/execution/input_review.py'),
    'tools/check_package.py': ('path', 'scripts/check_repository.py'),
    'tools/route_audit.py': ('path', 'provisioner/execution/route_audit.py'),
    'tools/guest_probe.py': ('path', 'provisioner/execution/guest_probe.py'),
    'tools/check_release.py': ('path', 'provisioner/execution/source_integrity.py'),
    'scripts/check_reservation_records.py': ('path', 'provisioner/allocations/reservation_evidence.py'),
    'scripts/check_ipam_allocation_records.py': ('path', 'provisioner/allocations/ipam_evidence.py'),
    'scripts/check_dns_registration_records.py': ('path', 'provisioner/allocations/dns_evidence.py'),
    'scripts/check_site_service_capacity.py': ('path', 'provisioner/allocations/capacity_evidence.py'),
    'scripts/check_site_service_eligibility.py': ('path', 'provisioner/allocations/site_eligibility.py'),
    'scripts/check_reservation_preflight.py': ('path', 'provisioner/allocations/reservation_preflight.py'),
    'scripts/check_ipam_allocation_preflight.py': ('path', 'provisioner/allocations/ipam_preflight.py'),
    'scripts/check_dns_registration_preflight.py': ('path', 'provisioner/allocations/dns_preflight.py'),
    'tools/terraform_catalog.py': ('path', 'provisioner/execution/terraform_catalog.py'),
    'tools/compile_wsd.py': ('path', 'provisioner/compiler/wsd.py'),
    'tools/old_compile.py': ('path', 'provisioner/compiler/wsd.py'),
    'tools/compile_wsd_v2.py': ('path', 'provisioner/compiler/wsd.py'),
    'provisioner/legacy': ('path', 'provisioner'),
    'tools/compatibility': ('path', 'migrate the caller, then delete'),
    'terraform/legacy': ('path', 'terraform/catalog.json'),
    'hosting.platform/v0': ('text', 'hosting.platform/v1'),
    'hosting-wsd-request/0': ('text', 'hosting.platform/v1'),
    'hosting apply --force': ('text', 'hosting apply'),
    'python -m provisioner.cli.main': ('text', 'python -m provisioner.cli'),
    'scripts/migrations/seed_completion_allocations.py':
        ('path', 'sources/assurance/implementation_allocation.json'),
    'provisioner/compiler/native.py': ('path', 'provisioner/adapters/base.py'),
    'scripts/check_platform_capabilities.py':
        ('path', 'provisioner/qualification/registry.py'),
    'scripts/check_platform_qualification.py':
        ('path', 'provisioner/qualification/native.py'),
    'scripts/check_version_source_provenance.py':
        ('path', 'provisioner/qualification/provenance.py'),
    'scripts/check_qualification_campaign_assurance.py':
        ('path', 'provisioner/qualification/campaign.py'),
    'scripts/check_target_selection_assurance.py':
        ('path', 'provisioner/qualification/target_selection.py'),
    'tools/dataset_acceptance.py': ('path', 'provisioner/execution/dataset_acceptance.py'),
    'tools/delivery_containment.py': ('path', 'provisioner/execution/delivery_containment.py'),
    'tools/delivery_run.py': ('path', 'provisioner/execution/delivery_run.py'),
    'tools/delivery_steps.py': ('path', 'provisioner/execution/delivery_steps.py'),
    'tools/dns_change.py': ('path', 'provisioner/execution/dns_change.py'),
    'tools/dns_propagation.py': ('path', 'provisioner/execution/dns_propagation.py'),
    'tools/edge_boot.py': ('path', 'provisioner/execution/edge_boot.py'),
    'tools/edge_contain.py': ('path', 'provisioner/execution/edge_contain.py'),
    'tools/edge_install.py': ('path', 'provisioner/execution/edge_install.py'),
    'tools/execution_journal.py': ('path', 'provisioner/execution/execution_journal.py'),
    'tools/guest_apply.py': ('path', 'provisioner/execution/guest_apply.py'),
    'tools/guest_inventory.py': ('path', 'provisioner/execution/guest_inventory.py'),
    'tools/guest_run.py': ('path', 'provisioner/execution/guest_run.py'),
    'tools/guest_services.py': ('path', 'provisioner/execution/guest_services.py'),
    'tools/netbox_dns.py': ('path', 'provisioner/execution/netbox_dns.py'),
    'tools/nft_edge.py': ('path', 'provisioner/execution/nft_edge.py'),
    'tools/nsx_domain_binding.py': ('path', 'provisioner/execution/nsx_domain_binding.py'),
    'tools/nsx_domain_observe.py': ('path', 'provisioner/execution/nsx_domain_observe.py'),
    'tools/nsx_domain_switch_observe.py': ('path', 'provisioner/execution/nsx_domain_switch_observe.py'),
    'tools/nsx_observe.py': ('path', 'provisioner/execution/nsx_observe.py'),
    'tools/nsx_segment_observe.py': ('path', 'provisioner/execution/nsx_segment_observe.py'),
    'tools/nsx_terraform_recovery.py': ('path', 'provisioner/execution/nsx_terraform_recovery.py'),
    'tools/nutanix_entity_activity.py': ('path', 'provisioner/execution/nutanix_entity_activity.py'),
    'tools/nutanix_flow_activity_observe.py': ('path', 'provisioner/execution/nutanix_flow_activity_observe.py'),
    'tools/nutanix_flow_observe.py': ('path', 'provisioner/execution/nutanix_flow_observe.py'),
    'tools/nutanix_flow_terraform_recovery.py': ('path', 'provisioner/execution/nutanix_flow_terraform_recovery.py'),
    'tools/nutanix_observe.py': ('path', 'provisioner/execution/nutanix_observe.py'),
    'tools/nutanix_task_tree.py': ('path', 'provisioner/execution/nutanix_task_tree.py'),
    'tools/nutanix_terraform_recovery.py': ('path', 'provisioner/execution/nutanix_terraform_recovery.py'),
    'tools/nutanix_vm_activity_observe.py': ('path', 'provisioner/execution/nutanix_vm_activity_observe.py'),
    'tools/nutanix_vm_observe.py': ('path', 'provisioner/execution/nutanix_vm_observe.py'),
    'tools/nutanix_vm_task_observe.py': ('path', 'provisioner/execution/nutanix_vm_task_observe.py'),
    'tools/openstack_observe.py': ('path', 'provisioner/execution/openstack_observe.py'),
    'tools/openstack_quota.py': ('path', 'provisioner/execution/openstack_quota.py'),
    'tools/operations_alerts.py': ('path', 'provisioner/execution/operations_alerts.py'),
    'tools/operations_review.py': ('path', 'provisioner/execution/operations_review.py'),
    'tools/owner_install.py': ('path', 'provisioner/execution/owner_install.py'),
    'tools/owner_revocations.py': ('path', 'provisioner/execution/owner_revocations.py'),
    'tools/owner_worker.py': ('path', 'provisioner/execution/owner_worker.py'),
    'tools/qualify_target.py': ('path', 'provisioner/execution/qualify_target.py'),
    'tools/readback_cli.py': ('path', 'provisioner/execution/readback_cli.py'),
    'tools/recovery_review.py': ('path', 'provisioner/execution/recovery_review.py'),
    'tools/remote_owner.py': ('path', 'provisioner/execution/remote_owner.py'),
    'tools/restic_run.py': ('path', 'provisioner/execution/restic_run.py'),
    'tools/restic_transfer.py': ('path', 'provisioner/execution/restic_transfer.py'),
    'tools/retirement.py': ('path', 'provisioner/execution/retirement.py'),
    'tools/runtime_build.py': ('path', 'provisioner/execution/runtime_build.py'),
    'tools/ssh_issuer.py': ('path', 'provisioner/execution/ssh_issuer.py'),
    'tools/state_backend.py': ('path', 'provisioner/execution/state_backend.py'),
    'tools/state_export.py': ('path', 'provisioner/execution/state_export.py'),
    'tools/state_project.py': ('path', 'provisioner/execution/state_project.py'),
    'tools/terraform_recovery_review.py': ('path', 'provisioner/execution/terraform_recovery_review.py'),
    'tools/vmware_network_binding.py': ('path', 'provisioner/execution/vmware_network_binding.py'),
    'tools/vsphere_clone_source.py': ('path', 'provisioner/execution/vsphere_clone_source.py'),
    'tools/vsphere_history.py': ('path', 'provisioner/execution/vsphere_history.py'),
    'tools/vsphere_network_observe.py': ('path', 'provisioner/execution/vsphere_network_observe.py'),
    'tools/vsphere_observe.py': ('path', 'provisioner/execution/vsphere_observe.py'),
    'tools/vsphere_port_observe.py': ('path', 'provisioner/execution/vsphere_port_observe.py'),
    'tools/vsphere_power.py': ('path', 'provisioner/execution/vsphere_power.py'),
    'tools/vsphere_recovery_devices.py': ('path', 'provisioner/execution/vsphere_recovery_devices.py'),
    'tools/vsphere_task_activity.py': ('path', 'provisioner/execution/vsphere_task_activity.py'),
    'tools/vsphere_task_observe.py': ('path', 'provisioner/execution/vsphere_task_observe.py'),
    'tools/vsphere_task_tree_observe.py': ('path', 'provisioner/execution/vsphere_task_tree_observe.py'),
    'tools/capacity.py': ('path', 'provisioner/allocations/capacity_owner.py'),
    'tools/capacity_demand.py': ('path', 'provisioner/allocations/capacity_demand.py'),
    'tools/netbox_ipam.py': ('path', 'provisioner/allocations/netbox_ipam.py'),
    'tools/service_http.py': ('path', 'provisioner/execution/service_http.py'),
}


class RetiredInterfaceTests(unittest.TestCase):
    def setUp(self):
        self.document = retirement._load_register(ROOT / 'provisioner/retired_interfaces.json')

    def test_exact_interfaces_kinds_and_replacements(self):
        entries = self.document['retiredInterfaces']
        actual = {row['interface']: (row['kind'], row['replacement']) for row in entries}
        self.assertEqual(actual, EXPECTED)
        self.assertEqual(len(entries), len(actual), 'Duplicate retirements are forbidden')

    def test_repository_has_no_retired_interfaces(self):
        report = retirement.check()
        self.assertEqual(report['status'], 'PASSED', report['issues'])
        self.assertEqual(report['issues'], [])
        self.assertEqual(report['interfaces_checked'], len(EXPECTED))
        self.assertEqual(report['native_infrastructure'], 'NOT_CONTACTED')

    def test_package_owners_are_real_modules_without_legacy_backreach(self):
        for old, (kind, replacement) in EXPECTED.items():
            if not replacement.startswith(('provisioner/qualification/', 'provisioner/execution/', 'provisioner/allocations/')):
                continue
            with self.subTest(owner=replacement):
                self.assertEqual(kind, 'path')
                self.assertFalse((ROOT / old).exists())
                module = ast.parse((ROOT / replacement).read_text(encoding='utf-8'))
                self.assertTrue(any(isinstance(node, (ast.FunctionDef, ast.ClassDef))
                                    for node in module.body))
                for node in ast.walk(module):
                    modules = ([alias.name for alias in node.names] if isinstance(node, ast.Import)
                               else [node.module or ''] if isinstance(node, ast.ImportFrom) else [])
                    self.assertFalse(any(name.split('.')[0] in {'scripts', 'tools'} for name in modules),
                                     f'{replacement} imports a legacy owner')

    def test_malformed_registers_are_rejected(self):
        invalid = []
        document = copy.deepcopy(self.document)
        document['format'] = 'unknown'
        invalid.append(document)
        document = copy.deepcopy(self.document)
        document['retiredInterfaces'] = []
        invalid.append(document)
        document = copy.deepcopy(self.document)
        document['retiredInterfaces'].append(copy.deepcopy(document['retiredInterfaces'][0]))
        invalid.append(document)
        document = copy.deepcopy(self.document)
        document['retiredInterfaces'][0]['kind'] = 'unknown'
        invalid.append(document)
        document = copy.deepcopy(self.document)
        del document['retiredInterfaces'][0]['replacement']
        invalid.append(document)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'register.json'
            for index, document in enumerate(invalid):
                with self.subTest(case=index):
                    path.write_text(json.dumps(document), encoding='utf-8')
                    with self.assertRaises(ValueError):
                        retirement._load_register(path)

    def _fixture_check(self, root: Path) -> dict:
        register = root / 'provisioner/retired_interfaces.json'
        register.parent.mkdir(parents=True, exist_ok=True)
        register.write_text(json.dumps(self.document), encoding='utf-8')
        with patch.object(retirement, 'ROOT', root), patch.object(retirement, 'REGISTER', register):
            return retirement.check(root=root, register=register)

    def test_each_retired_path_is_rejected_when_reintroduced(self):
        for interface, (kind, _) in EXPECTED.items():
            if kind != 'path':
                continue
            with self.subTest(interface=interface), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                path = root / interface
                path.parent.mkdir(parents=True, exist_ok=True)
                if path.suffix:
                    path.write_text('# forbidden wrapper\n', encoding='utf-8')
                else:
                    path.mkdir()
                report = self._fixture_check(root)
                self.assertEqual(report['status'], 'FAILED')
                self.assertEqual([(row['kind'], row['interface']) for row in report['issues']],
                                 [('REINTRODUCED_PATH', interface)])

    def test_each_retired_term_is_rejected_in_active_documents_and_sources(self):
        for interface, (kind, _) in EXPECTED.items():
            if kind != 'text':
                continue
            for relative in ('README.md', 'docs/current/example.md', 'provisioner/example.py'):
                with self.subTest(interface=interface, path=relative), tempfile.TemporaryDirectory() as directory:
                    root = Path(directory)
                    path = root / relative
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_text(interface + '\n', encoding='utf-8')
                    report = self._fixture_check(root)
                    self.assertEqual(report['status'], 'FAILED')
                    self.assertEqual([(row['interface'], row['path']) for row in report['issues']],
                                     [(interface, relative)])

    def test_frozen_specification_is_not_treated_as_an_active_caller(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / 'docs/deepseek-master-refactor-provisioning-prompt.md'
            path.parent.mkdir(parents=True)
            path.write_text('\n'.join(name for name, (kind, _) in EXPECTED.items() if kind == 'text'),
                            encoding='utf-8')
            self.assertEqual(self._fixture_check(root)['status'], 'PASSED')


if __name__ == '__main__':
    unittest.main()
