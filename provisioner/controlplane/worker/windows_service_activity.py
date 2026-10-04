"""Concrete existing-target Windows owners behind one fixed selected purpose."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType

from temporalio import activity

from provisioner.controlplane.authority.service import AuthorityDenied
from provisioner.controlplane.workflow.execution_selection import PostgresExecutionAuthority
from provisioner.controlplane.workflow.windows_service_job import (
    SERVICE_ACTIVITY, WindowsServiceStageRequest, WindowsServiceStageResult)
from provisioner.controlplane.workflow.windows_service_selection import (
    WindowsServiceSelection, validate_artifact)
from provisioner.controlplane.workflow.approval_gate import _valid_id
from provisioner.controlplane.jobs.repository import _digest
from provisioner.execution import delivery_steps
from provisioner.execution.run_files import digest, load_private, private_path, read_private, require
from .grants import GrantDenied
from .windows_commands import ScopedWindowsGuestRuntime
from .windows_services import ScopedWindowsServiceReadRuntime


@dataclass(frozen=True)
class WindowsServiceRuntimeBindings:
    bindings: object

    def __post_init__(self):
        require(type(self.bindings) is dict and len(self.bindings)<=100,
                'Bounded process-local enrolled Windows service owner bindings required')
        for key,owner in self.bindings.items():
            require(type(key) is tuple and len(key)==2
                    and all(_valid_id(value) for value in key)
                    and type(owner) in {ScopedWindowsGuestRuntime,ScopedWindowsServiceReadRuntime}
                    and key[1]==owner.command_runtime.grant.step_id
                    and (type(owner) is ScopedWindowsGuestRuntime or key[0]==owner.enrollment.admitted.job_id),
                    'A Windows service binding must use its actual current job/stage enrollment')
        object.__setattr__(self,'bindings',MappingProxyType(dict(self.bindings)))

    def selected(self,job_id,step_id): return self.bindings.get((job_id,step_id))


class WindowsServiceActivities:
    def __init__(self,authority,deliveries,inboxes,results,source_root,native:WindowsServiceRuntimeBindings):
        require(isinstance(authority,PostgresExecutionAuthority) and type(native) is WindowsServiceRuntimeBindings,
                'Actual root authority and independently enrolled fixed Windows owners required')
        self.authority,self.native=authority,native
        self.deliveries=private_path(deliveries,directory=True)
        self.inboxes=private_path(inboxes,directory=True)
        self.results=private_path(results,directory=True)
        self.source_root=Path(source_root)
        require(self.source_root.is_absolute(),'An explicit owned Windows command source root is required')

    @staticmethod
    def _held(request,reason):
        return WindowsServiceStageResult(request.input.admitted.job_id,request.step_id,'HELD',None,reason)

    @activity.defn(name=SERVICE_ACTIVITY)
    def run_step(self,request:WindowsServiceStageRequest)->WindowsServiceStageResult:
        require(type(request) is WindowsServiceStageRequest,'Exact fixed Windows activity references required')
        input=request.input
        try:
            # Read stages never acquire a mutation continuation, including when
            # the previous writer remains uncertain after remote contact.
            observer=request.step_id==input.service_steps[-1]
            gate=self.authority.require_observation if observer else self.authority.require_current
            plan,artifact=gate(input.admitted,input.selection_digest,'DISCOVER_READ' if observer else 'GUEST_CONFIG')
            validate_artifact(artifact); purpose=WindowsServiceSelection.from_record(artifact['windowsServices'])
            body=purpose.require_plan(plan,artifact)
            delivery=load_private(self.deliveries/(artifact['deliveryPlanDigest']+'.json'))
            steps=purpose.require_delivery(delivery)
            require(_digest(artifact)==input.selection_digest
                    and purpose.sha256==input.service_selection_digest and body['action']==input.action
                    and body['machineId']==input.machine_id and steps==tuple(input.service_steps)
                    and _digest(delivery)==artifact['deliveryPlanDigest']
                    and delivery['source_commit']==artifact['sourceCommit'] and delivery['scope']==artifact['executionScope'],
                    'Queued Windows service references differ from the current approved physical purpose')
            owner=self.native.selected(input.admitted.job_id,request.step_id)
            if owner is None: return self._held(request,'OPERATOR_HOLD')
            require(type(owner) is (ScopedWindowsServiceReadRuntime if observer else ScopedWindowsGuestRuntime)
                    and owner.command_runtime.authority is self.authority,
                    'This fixed Windows stage has another native owner or authority')
            row=body['read' if observer else 'write']
            require(owner.command_runtime.grant.operation_id==row['operationId'],
                    'Windows stage cannot borrow a different original native operation')
            retained=purpose.original if (not observer or body['write'] is None) else None
            require(owner.original_intent==retained,
                    'Windows owner changed the selected retained original native intent')
            step=next(row for row in delivery['steps'] if row['id']==request.step_id)
            inbox=private_path(self.inboxes/input.admitted.job_id,directory=True)
            packet=load_private(inbox/'steps'/request.step_id/'packet.json')
            require(packet['step_id']==request.step_id and packet['plan_sha256']==artifact['deliveryPlanDigest'],
                    'Windows packet belongs to another fixed selected stage or delivery')
            delivery_steps.validate_packet(step,packet,delivery,inbox,root=self.source_root)
            from provisioner.execution.windows_guest import WindowsGuestSelection
            purpose.require_guest(WindowsGuestSelection(read_private(
                packet['files']['windows_selection']['path'])),reader=observer)
            binding=artifact['stageBindings'][request.step_id]
            require(_digest(packet['parameters'])==binding['parametersDigest']
                    and {key:entry['sha256'] for key,entry in packet['files'].items()}==binding['inputDigests'],
                    'Actual Windows descriptor, input or fixed parameter bytes were not approved')
            directory=self.results/input.admitted.job_id/request.step_id
            if directory.exists():
                # Neither an interrupted write nor an old successful SCM read
                # grants another native invocation or current acceptance.
                return self._held(request,'RECOVERY_REQUIRED')
            parent=directory.parent
            if not parent.exists(): parent.mkdir(mode=0o700)
            private_path(parent,directory=True); directory.mkdir(mode=0o700)
            result,_names=owner.run_step(input.admitted,artifact,delivery,step,packet,directory,inbox,self.source_root)
            delivery_steps.typed_postcondition(step,result,directory,packet,delivery)
            completion=directory/'owner-completion.json'
            proof=digest(read_private(completion))
            return WindowsServiceStageResult(input.admitted.job_id,request.step_id,'STAGE_COMPLETED',proof,
                service_postconditions_observed=observer)
        except (GrantDenied,AuthorityDenied):
            return self._held(request,'AUTHORITY_REVOKED')
        except ValueError:
            return self._held(request,'VALIDATION_FAILED')
        except (OSError,RuntimeError):
            return self._held(request,'NATIVE_UNCERTAIN')
