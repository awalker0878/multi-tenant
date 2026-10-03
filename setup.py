"""Bundle reviewed planning resources in the distribution's own package.

No data directory is installed at site-packages root, where it could collide with
another distribution. Source references retain their relative paths inside the
resource package, so reviewed evidence links have the same meaning after install.
"""

import json
from pathlib import Path
from shutil import copy2, rmtree

from setuptools import setup
from setuptools.command.build_py import build_py


class BuildRuntime(build_py):
    """Copy reviewed inputs below the package that owns their resource API."""

    def run(self):
        source = Path(__file__).resolve().parent
        required = {
            'tools/__init__.py', 'provisioner/compiler/wsd.py', 'provisioner/execution/source_integrity.py',
            'scripts/__init__.py', 'provisioner/compiler/components.py',
            'provisioner/allocations/reservation_evidence.py',
            'provisioner/allocations/ipam_evidence.py', 'provisioner/allocations/dns_evidence.py',
            'provisioner/allocations/capacity_evidence.py', 'provisioner/allocations/site_eligibility.py',
            'provisioner/allocations/reservation_preflight.py', 'provisioner/allocations/ipam_preflight.py',
            'provisioner/allocations/dns_preflight.py',
            'provisioner/qualification/registry.py', 'provisioner/execution/terraform_catalog.py',
            'provisioner/execution/input_review.py',
            'provisioner/execution/flow_policy.py',
            'provisioner/execution/lifecycle_transition.py',
            'provisioner/execution/openstack_transition.py',
            'provisioner/execution/plan_review.py',
            'provisioner/execution/terraform_apply.py',
            'provisioner/execution/terraform_run.py',
            'provisioner/execution/wsd_handoff.py',

            'provisioner/execution/readback_core.py',
            'provisioner/execution/neutron_observe.py',
            'provisioner/execution/run_files.py',
            'provisioner/execution/route_record_review.py',

            'provisioner/allocations/transactions.py',
            'provisioner/controlplane/conversion/rehearsal.py',
            'provisioner/controlplane/discovery/monitor_runtime.py',
            'provisioner/controlplane/operations/action_gate.py',
            'provisioner/controlplane/workflow/application_job.py',
            'provisioner/controlplane/workflow/execution_selection.py',
            'provisioner/execution/dataset_acceptance.py',
            'provisioner/execution/delivery_containment.py',
            'provisioner/execution/delivery_run.py',
            'provisioner/execution/delivery_steps.py',
            'provisioner/execution/dns_change.py',
            'provisioner/execution/dns_propagation.py',
            'provisioner/execution/edge_boot.py',
            'provisioner/execution/edge_contain.py',
            'provisioner/execution/edge_install.py',
            'provisioner/execution/execution_journal.py',
            'provisioner/execution/guest_apply.py',
            'provisioner/execution/guest_inventory.py',
            'provisioner/execution/guest_run.py',
            'provisioner/execution/guest_services.py',
            'provisioner/execution/netbox_dns.py',
            'provisioner/execution/nft_edge.py',
            'provisioner/execution/nsx_domain_binding.py',
            'provisioner/execution/nsx_domain_observe.py',
            'provisioner/execution/nsx_domain_switch_observe.py',
            'provisioner/execution/nsx_observe.py',
            'provisioner/execution/nsx_segment_observe.py',
            'provisioner/execution/nsx_terraform_recovery.py',
            'provisioner/execution/nutanix_entity_activity.py',
            'provisioner/execution/nutanix_flow_activity_observe.py',
            'provisioner/execution/nutanix_flow_observe.py',
            'provisioner/execution/nutanix_flow_terraform_recovery.py',
            'provisioner/execution/nutanix_observe.py',
            'provisioner/execution/nutanix_task_tree.py',
            'provisioner/execution/nutanix_terraform_recovery.py',
            'provisioner/execution/nutanix_vm_activity_observe.py',
            'provisioner/execution/nutanix_vm_observe.py',
            'provisioner/execution/nutanix_vm_task_observe.py',
            'provisioner/execution/openstack_observe.py',
            'provisioner/execution/openstack_quota.py',
            'provisioner/execution/operations_alerts.py',
            'provisioner/execution/operations_review.py',
            'provisioner/execution/owner_install.py',
            'provisioner/execution/owner_revocations.py',
            'provisioner/execution/owner_worker.py',
            'provisioner/execution/qualify_target.py',
            'provisioner/execution/readback_cli.py',
            'provisioner/execution/recovery_review.py',
            'provisioner/execution/remote_owner.py',
            'provisioner/execution/restic_run.py',
            'provisioner/execution/restic_transfer.py',
            'provisioner/execution/retirement.py',
            'provisioner/execution/runtime_build.py',
            'provisioner/execution/ssh_issuer.py',
            'provisioner/execution/state_backend.py',
            'provisioner/execution/state_export.py',
            'provisioner/execution/state_project.py',
            'provisioner/execution/terraform_recovery_review.py',
            'provisioner/execution/vmware_network_binding.py',
            'provisioner/execution/vsphere_clone_source.py',
            'provisioner/execution/vsphere_history.py',
            'provisioner/execution/vsphere_network_observe.py',
            'provisioner/execution/vsphere_observe.py',
            'provisioner/execution/vsphere_port_observe.py',
            'provisioner/execution/vsphere_power.py',
            'provisioner/execution/vsphere_recovery_devices.py',
            'provisioner/execution/vsphere_task_activity.py',
            'provisioner/execution/vsphere_task_observe.py',
            'provisioner/execution/vsphere_task_tree_observe.py',
            'provisioner/migration/activities.py',
            'provisioner/qualification/mobility.py',

            'provisioner/allocations/capacity_demand.py',
            'provisioner/allocations/capacity_owner.py',
            'provisioner/allocations/netbox_ipam.py',
            'provisioner/execution/service_http.py',
            'sources/capabilities/platform_registry.json',
            'policy/rules/standards.json', 'profiles/security/catalog.json',
            'terraform/catalog.json', 'ansible/catalog.json', 'config/toolchain.json',
            'ansible/filter_plugins/guest_filters.py',
            'ansible/callback_plugins/hosting_guest_result.py',
        }
        terraform = json.loads((source / 'terraform/catalog.json').read_text(encoding='utf-8'))
        for entry in terraform['entries']:
            required.add(f"{entry['module']}/main.tf.json")
            required.add(f"{entry['root']}/main.tf.json")
        ansible = json.loads((source / 'ansible/catalog.json').read_text(encoding='utf-8'))
        required.update(f"ansible/{entry['path']}" for entry in ansible['playbooks'])
        required.update(f'ansible/roles/{name}/tasks/main.yml' for name in
                        ('linux_guest_baseline', 'linux_guest_services', 'linux_guest_backup'))
        # Capability validation checks that its reviewed evidence exists. Ship
        # the referenced documents, not the entire documentation workspace.
        runtime_docs = json.loads((source / 'hosting_resources/runtime-documents.json').read_text(encoding='utf-8'))
        if (not isinstance(runtime_docs, list) or not runtime_docs
                or any(not isinstance(path, str) or not path.startswith('docs/')
                       or Path(path).is_absolute() or '..' in Path(path).parts
                       or '\\' in path or ':' in path or path != Path(path).as_posix()
                       for path in runtime_docs)
                or len(runtime_docs) != len(set(runtime_docs))):
            raise ValueError('Invalid hosted runtime documentation manifest')
        evidence_docs = set(runtime_docs)
        def collect_docs(value):
            if isinstance(value, dict):
                for item in value.values():
                    collect_docs(item)
            elif isinstance(value, list):
                for item in value:
                    collect_docs(item)
            elif isinstance(value, str) and value.startswith('docs/'):
                path = Path(value)
                if path.is_absolute() or '..' in path.parts:
                    raise ValueError(f'Unsafe reviewed evidence reference: {value}')
                evidence_docs.add(value)

        for index in sorted((source / 'sources/capabilities').glob('*.json')):
            collect_docs(json.loads(index.read_text(encoding='utf-8')))
        required.update(evidence_docs)
        missing = sorted(path for path in required if not (source / path).is_file())
        if missing:
            raise FileNotFoundError(f'Incomplete runtime distribution: {missing}')

        build_root = Path(self.build_lib).resolve()
        source_trees = ('provisioner', 'tools', 'scripts', 'hosting_resources',
                        'profiles', 'policy', 'sources', 'terraform', 'ansible', 'config', 'docs')
        if (source.is_relative_to(build_root)
                or any(build_root.is_relative_to(source / name) for name in source_trees)):
            raise ValueError('Runtime build output overlaps source inputs')
        destination = build_root / 'hosting_resources' / '_assets'
        # Setuptools reuses build/lib. A previously built layout must not leak
        # shared data directories, deleted owners or their bytecode into the next
        # wheel. These four package trees are entirely regenerated by build_py.
        retired = [build_root / name for name in
                   ('profiles', 'policy', 'sources', 'terraform', 'ansible', 'config', 'docs',
                    'provisioner', 'tools', 'scripts', 'hosting_resources')]
        for path in retired:
            if path.is_symlink() or not path.resolve().is_relative_to(build_root.resolve()):
                raise ValueError(f'Unsafe runtime build directory: {path}')
            if path.exists():
                if not path.is_dir():
                    raise ValueError(f'Runtime build directory is not a directory: {path}')
                rmtree(path)

        super().run()
        for directory in ("profiles", "policy", "sources", "terraform", "ansible", "config"):
            for item in sorted((source / directory).rglob("*")):
                if not item.is_file() or "__pycache__" in item.parts:
                    continue
                target = destination / item.relative_to(source)
                target.parent.mkdir(parents=True, exist_ok=True)
                copy2(item, target)
        for relative in sorted(evidence_docs):
            target = destination / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            copy2(source / relative, target)


setup(cmdclass={"build_py": BuildRuntime})
