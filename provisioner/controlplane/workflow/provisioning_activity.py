"""Fixed admitted stages around existing allocation and delivery owners.

No input selects a module, callback, credential or native path. Process-local
native bindings must be enrolled by the installed service. A missing binding
holds before any owner dispatch. Offline stages retain their original receipts.
"""
from __future__ import annotations

from pathlib import Path
from types import MappingProxyType

from temporalio import activity

from provisioner.allocations.transactions import PoolDemand, ResourceBundle, ResourceTransactions
from provisioner.controlplane.authority.model import PlanScope
from provisioner.controlplane.authority.service import AuthorityDenied
from provisioner.controlplane.jobs.repository import _digest
from provisioner.execution import delivery_run, delivery_steps, readback_core as c
from provisioner.execution.run_files import load_private, private_path, require, sync_directory
from .application_job import ApplicationStageRequest, ApplicationStageResult
from .execution_selection import PostgresExecutionAuthority
from .approval_gate import _valid_id

_OFFLINE = frozenset({'acceptance', 'workload_inputs', 'platform_transition',
    'terraform_approval', 'guest_plan', 'dataset_acceptance', 'operations_review',
    'operations_alerts', 'retirement_review'})
_OPERATIONS = {'terraform_plan': 'DISCOVER_READ', 'terraform_apply': 'VM_CREATE',
    'target_campaign': 'DISCOVER_READ', 'guest_apply': 'GUEST_CONFIG',
    'edge_policy': 'POLICY_APPLY', 'openstack_quota': 'QUOTA_CHANGE',
    'ipam': 'IPAM_RESERVE', 'dns': 'DNS_CHANGE', 'dns_cutover': 'DNS_CHANGE',
    'dns_propagation': 'DISCOVER_READ', 'windows_guest_apply': 'GUEST_CONFIG',
    'windows_guest_remediate': 'GUEST_CONFIG', 'windows_guest_observe': 'DISCOVER_READ'}


class FileResourceBundleStore:
    def __init__(self, directory):
        self.directory = private_path(directory, directory=True)

    def __call__(self, admitted, selection):
        wanted = selection['resourceBundleDigest']
        record, pools = self._load(wanted)
        bundle = ResourceBundle(admitted, _digest(selection), record['workload_id'],
                                record['workload_revision'], tuple(pools))
        require((bundle.workload_id, bundle.workload_revision) ==
                (selection['workloadId'], selection['workloadRevision']), 'Resource workload selection changed')
        return bundle

    def load_document(self, resource_digest):
        """Validate reviewed demand without inventing an admitted job."""
        return self._load(resource_digest)[0]

    def _load(self, wanted):
        require(type(wanted) is str and c.HEX.fullmatch(wanted), 'Exact resource descriptor digest required')
        record = load_private(self.directory / (wanted + '.json'))
        require(type(record) is dict and set(record) ==
                {'format', 'workload_id', 'workload_revision', 'pools'}
                and record['format'] == 'hosting-resource-selection/1'
                and type(record['pools']) is list and 1 <= len(record['pools']) <= 20,
                'A protected exact resource descriptor is required')
        pools = []
        for row in record['pools']:
            require(type(row) is dict and set(row) == {'scope', 'catalog', 'inputs',
                'envelope_sha256', 'environment_key', 'capabilities', 'components'}
                and type(row['components']) is dict and set(row['components']) ==
                {'workload', 'staging', 'snapshots', 'retained-source'}, 'Exact resource purposes required')
            pools.append(PoolDemand.from_workload(scope=PlanScope(**row['scope']),
                catalog=row['catalog'], inputs=row['inputs'], envelope_sha256=row['envelope_sha256'],
                budgets={key: row['components'][key] for key in ('staging', 'snapshots', 'retained-source')},
                capabilities=tuple(row['capabilities']), environment_key=row['environment_key']))
        projected = {'format': 'hosting-resource-selection/1', 'workload_id': record['workload_id'],
            'workload_revision': record['workload_revision'], 'pools': [pool.document() for pool in pools]}
        require(c.digest(projected) == wanted and projected == record,
                'The selected resource demand or reviewed budget changed')
        require(_valid_id(record['workload_id']) and type(record['workload_revision']) is int
                and record['workload_revision'] > 0, 'Exact resource workload revision required')
        return record, pools


class ProvisioningRuntimeBindings:
    """Only concrete enrolled owners may dispatch a reviewed native stage."""
    def __init__(self, bindings=None):
        from provisioner.controlplane.reconciliation.planned_terraform import PlannedTerraformRuntime
        from provisioner.controlplane.reconciliation.service_runtime import EnrolledServiceProvisioningRuntime
        from provisioner.controlplane.reconciliation.service_propagation import EnrolledDnsPropagationRuntime
        from provisioner.controlplane.worker.windows_commands import ScopedWindowsGuestRuntime
        from provisioner.controlplane.worker.windows_services import ScopedWindowsServiceReadRuntime
        from provisioner.migration.provisioning import ObservedProvisioningRuntime
        bindings = {} if bindings is None else dict(bindings)
        require(all(isinstance(key, tuple) and len(key) == 2 and
                    all(_valid_id(value) for value in key) and
                    isinstance(owner, (PlannedTerraformRuntime, ObservedProvisioningRuntime,
                                       EnrolledServiceProvisioningRuntime, EnrolledDnsPropagationRuntime,
                                       ScopedWindowsGuestRuntime, ScopedWindowsServiceReadRuntime))
                    for key, owner in bindings.items()), 'Typed enrolled native stage owners required')
        self.bindings = MappingProxyType(bindings)

    def selected(self, job_id, step_id):
        return self.bindings.get((job_id, step_id))


class ApplicationProvisioningActivities:
    def __init__(self, *, authority, resources, bundles, delivery_directory,
                 inbox_directory, journals_directory, source_root, native_bindings,
                 migration_selections=None, staged_resources=None):
        require(isinstance(authority, PostgresExecutionAuthority)
                and isinstance(resources, ResourceTransactions)
                and isinstance(bundles, FileResourceBundleStore)
                and isinstance(native_bindings, ProvisioningRuntimeBindings),
                'Concrete installed authority, allocation and native owners required')
        self.authority, self.resources, self.bundles = authority, resources, bundles
        self.deliveries = private_path(delivery_directory, directory=True)
        self.inboxes = private_path(inbox_directory, directory=True)
        self.journals = private_path(journals_directory, directory=True)
        self.root = Path(source_root)
        self.native_bindings = native_bindings
        if migration_selections is not None:
            from provisioner.migration.activities import FileMigrationSelectionStore
            require(isinstance(migration_selections, FileMigrationSelectionStore),
                    'Concrete protected lifecycle descriptor owner required')
        self.migration_selections = migration_selections
        from types import MappingProxyType
        from provisioner.controlplane.reconciliation.staged_resources import StagedApplicationResourceAuthority
        owners = {} if staged_resources is None else dict(staged_resources)
        require(all(type(owner) is StagedApplicationResourceAuthority and owner.admitted.job_id == job_id
                    and owner.resources is resources and owner.connect is authority.connect
                    for job_id, owner in owners.items()),
                'Current cutover requires actual immutable original resource parents')
        self.staged_resources = MappingProxyType(owners)

    def _require_ready(self, admitted, selection):
        if selection['driver'] in {'openstack-linux-application-cutover/1', 'openstack-linux-application-database/1'}:
            owner = self.staged_resources.get(admitted.job_id)
            require(owner is not None, 'The concrete independently revalidated staged resource owner is required')
            owner.bundle_for(admitted, selection)
            return owner.require_ready(admitted, selection)
        return self.resources.require_ready(self.bundles(admitted, selection))

    @staticmethod
    def _held(request, reason, hold_code=None):
        return ApplicationStageResult('HELD', request.admitted.job_id, request.step_id, reason,
                                      hold_code=hold_code)

    @activity.defn(name='application_reserve_resources')
    def reserve_resources(self, request: ApplicationStageRequest) -> ApplicationStageResult:
        require(isinstance(request, ApplicationStageRequest) and not request.step_id,
                'Typed admitted resource phase required')
        try:
            _, selection = self.authority.require_current(request.admitted, request.selection_digest, 'IPAM_RESERVE')
            require(selection['driver'] in {'openstack-linux-rebuild/1', 'openstack-linux-application-staging/1'}
                    and 'resourceRecoverySelectionDigest' not in selection,
                    'A current cutover or recovery cannot reserve the original target again')
            bundle = self.bundles(request.admitted, selection)
            result = self.resources.reserve(bundle)
            self.resources.require_ready(bundle)
            return ApplicationStageResult('STAGE_VERIFIED', request.admitted.job_id, '',
                                           evidence_digest=_digest(result))
        except AuthorityDenied:
            return self._held(request, 'AUTHORITY_REVOKED')
        except Exception:
            return self._held(request, 'CAPACITY_UNAVAILABLE')

    @activity.defn(name='application_provision_step')
    def provision_step(self, request: ApplicationStageRequest) -> ApplicationStageResult:
        from provisioner.migration.provisioning import ProvisioningHeld
        require(isinstance(request, ApplicationStageRequest) and request.step_id,
                'Typed selected provisioning step required')
        try:
            # The original artifact determines the kind; an activity argument
            # cannot request a different platform action.
            selection = self.authority.selections.load_verified(request.selection_digest)
            if selection.get('applicationLifecycleSelectionDigest') is not None:
                require(self.migration_selections is not None,
                        'The phase-owned lifecycle selection is unavailable')
                lifecycle = self.migration_selections.lifecycle(
                    selection['applicationLifecycleSelectionDigest']).to_dict()
                deferred = {step_id for member in lifecycle['members']
                            for step_id in member['traffic_steps'].values()}
                require(request.step_id not in deferred,
                        'Application traffic can be dispatched only by its exact lifecycle phase')
            binding = selection['stageBindings'].get(request.step_id)
            require(binding is not None, 'Step is absent from the approved selected graph')
            kind = binding['kind']
            if selection['driver'] in {'openstack-linux-application-cutover/1',
                    'openstack-linux-application-database/1'} and kind == 'guest_apply':
                staged = self.staged_resources.get(request.admitted.job_id)
                if staged is None or not callable(getattr(staged, 'require_guest_ready', None)):
                    return self._held(request, 'OPERATOR_HOLD', 'ISOLATED_MANAGEMENT_BOOTSTRAP_REQUIRED')
                staged.require_guest_ready(request.admitted, selection)
            from .application_selection import CREATION_STAGES
            require(selection['driver'] not in {'openstack-linux-application-cutover/1',
                    'openstack-linux-application-database/1'} or kind not in CREATION_STAGES,
                    'A current staged cutover cannot create or reserve the original target again')
            require('resourceRecoverySelectionDigest' not in selection
                    and 'applicationRecoverySelectionDigest' not in selection,
                    'Resource recovery requires its fixed original-intent workflow')
            require(kind in _OFFLINE | _OPERATIONS.keys(), 'This stage has no admitted concrete owner')
            operation = _OPERATIONS.get(kind, 'DISCOVER_READ')
            _, selection = self.authority.require_current(request.admitted, request.selection_digest, operation)
            self._require_ready(request.admitted, selection)
            delivery = load_private(self.deliveries / (selection['deliveryPlanDigest'] + '.json'))
            delivery_run.validate(delivery)
            require(_digest(delivery) == selection['deliveryPlanDigest'], 'Delivery graph content changed')
            step = next(s for s in delivery['steps'] if s['id'] == request.step_id)
            require(step['kind'] == kind, 'Selected stage owner changed')
            native = self.native_bindings.selected(request.admitted.job_id, request.step_id)
            if kind not in _OFFLINE and native is None:
                return self._held(request, 'OPERATOR_HOLD', 'NATIVE_STAGE_OWNER_UNAVAILABLE')
            inbox = private_path(self.inboxes / request.admitted.job_id, directory=True)
            ledger = self.journals / request.admitted.job_id
            if not ledger.exists():
                ledger.mkdir(mode=0o700)
                sync_directory(ledger.parent)
            private_path(ledger, directory=True)

            def guard(selected_step, packet):
                require(selected_step['id'] == request.step_id,
                        'An earlier unresolved stage must be reconciled independently')
                self.authority.require_packet(request.admitted, request.selection_digest,
                    delivery, selected_step, packet, operation)
                self._require_ready(request.admitted, selection)

            def owner(selected_step, packet, directory, base, plan, root, **keywords):
                require(selected_step['id'] == request.step_id, 'A different native step cannot be dispatched')
                if kind in _OFFLINE:
                    return delivery_steps.dispatch(selected_step, packet, directory, base, plan, root, **keywords)
                return native.run_step(request.admitted, selection, plan, selected_step,
                                       packet, directory, base, root)

            def recover_original(selected_step, packet, directory, base, plan, root, **keywords):
                require(selected_step['id'] == request.step_id,
                        'An earlier unresolved native stage needs its own original-operation recovery')
                if kind in _OFFLINE:
                    return delivery_steps.recover(selected_step, packet, directory, base, plan, root, **keywords)
                require(callable(getattr(native, 'recover_step', None)),
                        'The enrolled native owner must independently recover the original operation')
                return native.recover_step(request.admitted, selection, plan, selected_step,
                                           packet, directory, base, root, **keywords)

            result = delivery_run.run(delivery, inbox, ledger, execute=True, root=self.root,
                stop_after_step=request.step_id, effect_guard=guard, dispatch_owner=owner,
                recover_owner=recover_original)
            if result['status'] != 'STEP_EVIDENCE_RETAINED':
                return self._held(request, 'OPERATOR_HOLD')
            return ApplicationStageResult('STAGE_VERIFIED', request.admitted.job_id, request.step_id,
                                           evidence_digest=result['evidence_digest'])
        except AuthorityDenied:
            return self._held(request, 'AUTHORITY_REVOKED')
        except ProvisioningHeld as held:
            return self._held(request, 'OPERATOR_HOLD', held.hold_code)
        except Exception:
            return self._held(request, 'NATIVE_UNCERTAIN')
