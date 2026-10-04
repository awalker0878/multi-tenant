"""Exact-binding Temporal start adapter for the B09 transactional outbox.

The synchronous B09 dispatcher calls this from a worker thread/process without
an active event loop. Every external RPC has a deadline. A duplicate Workflow ID
is accepted only after Temporal describes the pinned run and its immutable start
memo exactly matches the committed outbox payload. Missing history is an error,
never proof that the caller may start another run.
"""
from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path

from temporalio.client import Client, TLSConfig, WorkflowExecutionStatus
from temporalio.common import WorkflowIDConflictPolicy, WorkflowIDReusePolicy
from temporalio.exceptions import WorkflowAlreadyStartedError

from provisioner.controlplane.jobs.repository import AdmissionConflict, StartReceipt, _digest

from .admitted_job import AdmittedInput, AdmittedMigrationJob
from .approval_gate import GateResult, _valid_id
from .application_job import ApplicationJobInput, ApplicationJobResult, OpenStackApplicationMigration
from .application_staging_job import ApplicationStagingInput, ApplicationStagingResult, OpenStackApplicationStaging
from .application_cutover_job import ApplicationCutoverInput, OpenStackStagedApplicationCutover
from .resource_recovery_job import ResourceRecoveryInput, ResourceRecoveryResult, SelectedResourceRecovery
from .application_recovery_job import (ApplicationRecoveryInput, ApplicationRecoveryResult,
                                      SelectedApplicationPostwriteRecovery)
from .windows_service_job import WindowsServiceInput, WindowsServiceResult, SelectedWindowsExistingServices
from .cold_capture_job import ColdCaptureInput, ColdCaptureResult, SelectedColdCapture

_PAYLOAD_KEYS = frozenset({'format', 'job_id', 'organization_id', 'tenant_id',
                           'plan_id', 'plan_revision', 'plan_digest', 'revocation_epoch'})
_DIGEST = re.compile(r'[0-9a-f]{64}')
_MEMO_KEY = 'hosting_job_binding_v1'
_SELECTED_WORKFLOWS = {
    'OpenStackApplicationMigration': (ApplicationJobInput, OpenStackApplicationMigration, ApplicationJobResult),
    'OpenStackApplicationStaging': (ApplicationStagingInput, OpenStackApplicationStaging, ApplicationStagingResult),
    'OpenStackStagedApplicationCutover': (ApplicationCutoverInput, OpenStackStagedApplicationCutover, ApplicationJobResult),
    'SelectedResourceRecovery': (ResourceRecoveryInput, SelectedResourceRecovery, ResourceRecoveryResult),
    'SelectedApplicationPostwriteRecovery': (ApplicationRecoveryInput, SelectedApplicationPostwriteRecovery,
                                            ApplicationRecoveryResult),
    'SelectedWindowsExistingServices': (WindowsServiceInput, SelectedWindowsExistingServices, WindowsServiceResult),
    'SelectedColdCapture': (ColdCaptureInput, SelectedColdCapture, ColdCaptureResult),
}
_SELECTED_INPUTS = tuple(row[0] for row in _SELECTED_WORKFLOWS.values())
_SELECTED_DIGESTS = ('lifecycle_selection_digest', 'staging_selection_digest',
                     'database_selection_digest', 'recovery_selection_digest', 'service_selection_digest',
                     'cold_selection_digest')


def _application_input_digest(selected):
    from dataclasses import asdict
    record = asdict(selected)
    # Preserve the exact original digest for pre-lifecycle histories.
    for field in (*_SELECTED_DIGESTS, 'database_member_id'):
        if record.get(field) is None:
            record.pop(field, None)
    return _digest(record)


@dataclass(frozen=True)
class TemporalConnection:
    target_host: str
    namespace: str
    task_queue: str
    server_ca: Path | None = None
    client_cert: Path | None = None
    client_key: Path | None = None
    server_name: str | None = None
    insecure_loopback_for_tests: bool = False
    rpc_timeout_seconds: int = 10

    def __post_init__(self) -> None:
        if not self.target_host or not _valid_id(self.namespace) or not _valid_id(self.task_queue):
            raise ValueError('Temporal host, namespace and task queue are required')
        if type(self.rpc_timeout_seconds) is not int or not 1 <= self.rpc_timeout_seconds <= 60:
            raise ValueError('Temporal RPC timeout must be between 1 and 60 seconds')
        if self.insecure_loopback_for_tests:
            if self.target_host.split(':')[0] not in ('127.0.0.1', 'localhost', '[::1]'):
                raise ValueError('Insecure Temporal is only allowed on loopback in tests')
        elif not (self.server_ca and self.client_cert and self.client_key and self.server_name):
            raise ValueError('A server CA, client certificate, key and verified server name are required')

    def tls(self) -> TLSConfig | None:
        if self.insecure_loopback_for_tests:
            return None
        # Read credentials only into the client process. Never serialize them
        # into Temporal history, a job payload, a memo or logs.
        return TLSConfig(server_root_ca_cert=Path(self.server_ca).read_bytes(),
                         client_cert=Path(self.client_cert).read_bytes(),
                         client_private_key=Path(self.client_key).read_bytes(),
                         verification_server_name=self.server_name)


def _admitted_input(workflow_id: str, payload: dict) -> AdmittedInput:
    if (type(payload) is not dict or frozenset(payload) != _PAYLOAD_KEYS
            or payload.get('format') != 'hosting-workflow-start/1'
            or payload.get('job_id') != workflow_id
            or not _valid_id(workflow_id)
            or type(payload.get('revocation_epoch')) is not int
            or payload['revocation_epoch'] < 0):
        raise AdmissionConflict('Invalid exact outbox workflow binding')
    try:
        return AdmittedInput(workflow_id, payload['organization_id'], payload['tenant_id'],
                             payload['plan_id'], payload['plan_revision'],
                             payload['plan_digest'], payload['revocation_epoch'],
                             _digest(payload))
    except (ValueError, TypeError, KeyError) as exc:
        raise AdmissionConflict('Invalid exact outbox workflow binding') from exc


class TemporalWorkflowStarter:
    """B09 DurableWorkflowStarter using an actual Temporal namespace.

    Construct one per dispatcher with credentials confined to that dispatcher.
    The adapter only launches an admitted-job authority gate, never a platform
    action. The approval-wait workflow is a separate B08 durability scenario.
    """

    def __init__(self, connection: TemporalConnection, *, application_selector=None):
        if application_selector is not None and not callable(application_selector):
            raise TypeError('A trusted current-plan selector is required')
        self.connection = connection
        self.application_selector = application_selector

    def start(self, *, namespace: str, workflow_id: str, payload: dict) -> StartReceipt:
        if namespace != self.connection.namespace:
            raise AdmissionConflict('Outbox and Temporal namespaces differ')
        gate = _admitted_input(workflow_id, payload)
        selected = self.application_selector(gate) if self.application_selector is not None else None
        if selected is not None and (type(selected) not in _SELECTED_INPUTS
                                     or selected.admitted != gate):
            raise AdmissionConflict('Application graph belongs to another admitted job')
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(self._start(gate, namespace, selected))
        raise RuntimeError('Run the synchronous dispatcher outside an asyncio event loop')

    async def _start(self, gate: AdmittedInput, namespace: str,
                     selected=None) -> StartReceipt:
        client = await Client.connect(self.connection.target_host, namespace=namespace,
                                      tls=self.connection.tls())
        deadline = timedelta(seconds=self.connection.rpc_timeout_seconds)
        binding = {'job_id': gate.job_id, 'organization_id': gate.organization_id,
                   'tenant_id': gate.tenant_id, 'plan_id': gate.plan_id,
                   'plan_revision': gate.plan_revision, 'plan_digest': gate.plan_digest,
                   'revocation_epoch': gate.revocation_epoch,
                   'payload_digest': gate.payload_digest}
        workflow_run = AdmittedMigrationJob.run
        workflow_type = 'AdmittedMigrationJob'
        argument = gate
        if selected is not None:
            binding['application_input_digest'] = _application_input_digest(selected)
            binding['selection_digest'] = selected.selection_digest
            for field in _SELECTED_DIGESTS:
                value = getattr(selected, field, None)
                if value is not None:
                    binding[field] = value
            if isinstance(selected, (ResourceRecoveryInput, ApplicationRecoveryInput)):
                binding['original_job_id'] = selected.original_job_id
            workflow_type, (_, workflow_class, _) = next(
                (name, row) for name, row in _SELECTED_WORKFLOWS.items() if type(selected) is row[0])
            workflow_run = workflow_class.run
            argument = selected
        try:
            handle = await client.start_workflow(
                workflow_run, argument, id=gate.job_id,
                task_queue=self.connection.task_queue,
                id_reuse_policy=WorkflowIDReusePolicy.REJECT_DUPLICATE,
                id_conflict_policy=WorkflowIDConflictPolicy.FAIL,
                memo={_MEMO_KEY: binding}, rpc_timeout=deadline)
            run_id = handle.result_run_id
        except WorkflowAlreadyStartedError as exc:
            # If the server cannot identify which run collided, describe the
            # latest retained run and still require its exact memo to match.
            run_id = exc.run_id
        handle = client.get_workflow_handle(gate.job_id, run_id=run_id)
        description = await handle.describe(rpc_timeout=deadline)
        stored_binding = await description.memo_value(_MEMO_KEY, None)
        if (not description.run_id or (run_id and description.run_id != run_id)
                or description.id != gate.job_id
                or description.workflow_type != workflow_type
                or stored_binding != binding):
            raise AdmissionConflict('Temporal workflow ID belongs to a different job binding')
        return StartReceipt(namespace, gate.job_id, description.run_id, gate.job_id,
                            gate.plan_id, gate.plan_revision, gate.plan_digest,
                            gate.payload_digest)

    def completed_gate(self, receipt: StartReceipt) -> GateResult | None:
        """Read only the pinned completed run; None means still in progress."""
        if receipt.namespace != self.connection.namespace:
            raise AdmissionConflict('Stored run belongs to another namespace')
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(self._completed_gate(receipt))
        raise RuntimeError('Call the synchronous result reader outside an asyncio event loop')

    async def _completed_gate(self, receipt: StartReceipt) -> GateResult | None:
        client = await Client.connect(self.connection.target_host,
                                      namespace=receipt.namespace, tls=self.connection.tls())
        handle = client.get_workflow_handle(receipt.workflow_id, run_id=receipt.run_id,
                                            result_type=GateResult)
        deadline = timedelta(seconds=self.connection.rpc_timeout_seconds)
        description = await handle.describe(rpc_timeout=deadline)
        memo = await description.memo_value(_MEMO_KEY, None)
        if (description.run_id != receipt.run_id
                or description.workflow_type != 'AdmittedMigrationJob'
                or not isinstance(memo, dict)
                or (memo.get('job_id'), memo.get('plan_id'),
                    memo.get('plan_revision'), memo.get('plan_digest'),
                    memo.get('payload_digest')) !=
                   (receipt.job_id, receipt.plan_id, receipt.plan_revision,
                    receipt.plan_digest, receipt.payload_digest)):
            raise AdmissionConflict('Completed Temporal run has a foreign binding')
        if description.status == WorkflowExecutionStatus.RUNNING:
            return None
        if description.status != WorkflowExecutionStatus.COMPLETED:
            return GateResult('HELD', receipt.job_id, receipt.plan_id,
                              receipt.plan_revision, receipt.plan_digest)
        result = await handle.result(follow_runs=False, rpc_timeout=deadline)
        if (not isinstance(result, GateResult)
                or (result.job_id, result.plan_id, result.plan_revision,
                    result.plan_digest) != (receipt.job_id, receipt.plan_id,
                                            receipt.plan_revision, receipt.plan_digest)
                or result.status not in ('GATE_PASSED', 'HELD')):
            raise AdmissionConflict('Temporal result does not bind the admitted job')
        return result

    def completed_job(self, receipt: StartReceipt) -> GateResult | ApplicationJobResult | None:
        """Read the exact run and retain its original declared workflow type."""
        if receipt.namespace != self.connection.namespace:
            raise AdmissionConflict('Stored run belongs to another namespace')
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(self._completed_job(receipt))
        raise RuntimeError('Call result readback outside an asyncio event loop')

    async def _completed_job(self, receipt):
        client = await Client.connect(self.connection.target_host,
            namespace=receipt.namespace, tls=self.connection.tls())
        deadline = timedelta(seconds=self.connection.rpc_timeout_seconds)
        handle = client.get_workflow_handle(receipt.workflow_id, run_id=receipt.run_id)
        description = await handle.describe(rpc_timeout=deadline)
        if description.workflow_type == 'AdmittedMigrationJob':
            return await self._completed_gate(receipt)
        memo = await description.memo_value(_MEMO_KEY, None)
        selected_type = _SELECTED_WORKFLOWS.get(description.workflow_type)
        if (selected_type is None
                or description.run_id != receipt.run_id or description.id != receipt.workflow_id
                or not isinstance(memo, dict) or not _DIGEST.fullmatch(memo.get('selection_digest', ''))
                or not _DIGEST.fullmatch(memo.get('application_input_digest', ''))
                or (memo.get('job_id'), memo.get('plan_id'), memo.get('plan_revision'),
                    memo.get('plan_digest'), memo.get('payload_digest')) !=
                    (receipt.job_id, receipt.plan_id, receipt.plan_revision,
                     receipt.plan_digest, receipt.payload_digest)):
            raise AdmissionConflict('Completed application run has a foreign original binding')
        mandatory = {
            'OpenStackStagedApplicationCutover': ('lifecycle_selection_digest', 'staging_selection_digest'),
            'SelectedResourceRecovery': ('recovery_selection_digest',),
            'SelectedApplicationPostwriteRecovery': ('lifecycle_selection_digest', 'recovery_selection_digest'),
            'SelectedWindowsExistingServices': ('service_selection_digest',),
            'SelectedColdCapture': ('cold_selection_digest',),
        }.get(description.workflow_type, ())
        if (any(not isinstance(memo.get(field), str) or not _DIGEST.fullmatch(memo[field])
                for field in mandatory)
                or (description.workflow_type in {'SelectedResourceRecovery', 'SelectedApplicationPostwriteRecovery'} and
                    (not _valid_id(memo.get('original_job_id')) or memo['original_job_id'] == receipt.job_id))):
            raise AdmissionConflict('Selected workflow lost its exact approved original purpose')
        if description.status == WorkflowExecutionStatus.RUNNING:
            return None
        result_type = selected_type[2]
        if description.status != WorkflowExecutionStatus.COMPLETED:
            if result_type is ApplicationStagingResult:
                return ApplicationStagingResult(receipt.job_id, receipt.plan_id, receipt.plan_revision,
                    receipt.plan_digest, memo['selection_digest'], 'HELD', 'VERIFY',
                    'NATIVE_UNCERTAIN', None, 0, 0)
            if result_type is ResourceRecoveryResult:
                return ResourceRecoveryResult(receipt.job_id, receipt.plan_id, receipt.plan_revision,
                    receipt.plan_digest, memo['selection_digest'], memo['recovery_selection_digest'],
                    memo['original_job_id'], 'HELD', 'RECONCILE', 0, 0, None, 'NATIVE_UNCERTAIN')
            if result_type is ApplicationRecoveryResult:
                return ApplicationRecoveryResult(receipt.job_id, receipt.plan_id, receipt.plan_revision,
                    receipt.plan_digest, memo['selection_digest'], memo['lifecycle_selection_digest'],
                    memo['recovery_selection_digest'], memo['original_job_id'], 'HELD', 'RECONCILE',
                    0, 0, None, 'NATIVE_UNCERTAIN')
            if result_type is WindowsServiceResult:
                return WindowsServiceResult(receipt.job_id, receipt.plan_id, receipt.plan_revision,
                    receipt.plan_digest, memo['selection_digest'], memo['service_selection_digest'],
                    'HELD', 'VERIFY', 'NATIVE_UNCERTAIN', None, 0, 0, False)
            if result_type is ColdCaptureResult:
                return ColdCaptureResult(receipt.job_id, receipt.plan_id, receipt.plan_revision,
                    receipt.plan_digest, memo['selection_digest'], memo['cold_selection_digest'],
                    'HELD', 'VERIFY', 0, 0, None, None, 'NATIVE_UNCERTAIN')
            return ApplicationJobResult(receipt.job_id, receipt.plan_id, receipt.plan_revision,
                receipt.plan_digest, memo['selection_digest'], 'HELD', 'VERIFY',
                'NATIVE_UNCERTAIN', None, 0, 0, None, memo.get('lifecycle_selection_digest'),
                memo.get('staging_selection_digest'), memo.get('database_selection_digest'))
        typed = client.get_workflow_handle(receipt.workflow_id, run_id=receipt.run_id,
                                           result_type=result_type)
        result = await typed.result(follow_runs=False, rpc_timeout=deadline)
        if (not isinstance(result, result_type)
                or (result.job_id, result.plan_id, result.plan_revision, result.plan_digest,
                    result.selection_digest) != (receipt.job_id, receipt.plan_id,
                    receipt.plan_revision, receipt.plan_digest, memo['selection_digest'])
                or any(getattr(result, field, None) != memo.get(field) for field in _SELECTED_DIGESTS)
                or (result_type in {ResourceRecoveryResult, ApplicationRecoveryResult}
                    and result.original_job_id != memo.get('original_job_id'))
                or (result_type is ApplicationJobResult and result.status == 'SUCCEEDED'
                    and not _DIGEST.fullmatch(memo.get('lifecycle_selection_digest', '')))):
            raise AdmissionConflict('Application result differs from the original admitted job')
        return result
