"""Confirm actual target and retained-source occupancy in the existing charge.

The two concrete independent native readers own their evidence separately.
Neither a Terraform exit code nor a completed delivery packet confirms capacity.
Temporary/snapshot purposes remain held without their actual counted owner.
"""
from dataclasses import asdict

from provisioner.allocations.transactions import ResourceBundle,ResourceTransactions,ResourceUnits
from provisioner.controlplane.persistence import NativeBinding
from provisioner.execution.run_files import require
from .adapters.openstack_readback import OpenStackNativeReadbackOwner
from .adapters.vmware_source_capacity import SourceCapacityReadRuntime
from .planned import NativeCreationObservation


class ApplicationResourceAccounting:
    def __init__(self,*,resources,destination,source=None):
        require(isinstance(resources,ResourceTransactions) and type(destination) is OpenStackNativeReadbackOwner
                and (source is None or type(source) is SourceCapacityReadRuntime),
                'Actual allocation owner and separately enrolled target/source native readers are required')
        self.resources,self.destination,self.source=resources,destination,source

    def verify_resource_observation(self,cursor,bundle,action,observation):
        require(isinstance(bundle,ResourceBundle) and action=='confirm',
                'Application occupancy cannot authorize native cleanup or capacity refund')
        receipts=self.resources._require_accounted(bundle)['receipts']
        selected=[pool for pool,receipt in zip(bundle.pools,receipts)
                  if receipt['reservation_id']==observation.reservation_id]
        require(len(selected)==1,'An independent observation belongs to another original resource charge')
        pool=selected[0]
        if pool.scope==self.destination.enrollment.scope:
            require(pool.inputs is not None and all(value==ResourceUnits() for value in
                    (pool.staging,pool.snapshots,pool.retained_source)),
                    'Target temporary and snapshot purposes require their separate counted native owner')
            self.destination.verify_resource_observation(cursor,bundle,action,observation)
        else:
            require(self.source is not None and pool.scope==self.source.enrollment.scope and pool.inputs is None,
                    'The retained source charge needs its separately enrolled exact native occupancy owner')
            self.source.verify_resource_observation(cursor,bundle,action,observation)

    def confirm_creation(self,runtime,admitted,artifact,bundle,observation):
        from .planned_terraform import PlannedTerraformRuntime
        require(type(runtime) is PlannedTerraformRuntime and isinstance(observation,NativeCreationObservation)
                and bundle.admitted==admitted and runtime.observer is self.destination
                and runtime.registry.leases.resources is self.resources,
                'Only the exact independently acknowledged native creation can confirm this original charge')
        operation=runtime.registry.get(runtime.context,runtime.grant.operation_id)
        require(operation.state=='RESOLVED' and operation.outcome=='EFFECT_PRESENT'
                and operation.job_id==admitted.job_id and operation.request_digest==runtime.lease.request_digest,
                'Unresolved native creation must retain its original charge without confirming occupancy')
        plan,selection=runtime.authority.require_observation(admitted,bundle.selection_digest,'DISCOVER_READ')
        require(selection==artifact,'The original charged application changed its protected selection')
        # Confirmation precedes TARGET history association. Both original
        # source and target are independently recontacted by the locked owner.
        accounted=self.resources.require_ready(bundle);observations=[]
        sources=tuple(NativeBinding(row['sourceBinding']['platformFamily'],row['sourceBinding']['endpointId'],
            row['sourceBinding']['nativeScopeId'],'vm',row['sourceBinding']['nativeId'])
            for row in plan['spec']['machineMappings'])
        for pool,receipt in zip(bundle.pools,accounted['receipts']):
            if pool.scope==self.destination.enrollment.scope:
                require(pool.inputs is not None and all(value==ResourceUnits() for value in
                    (pool.staging,pool.snapshots,pool.retained_source)),
                    'Nonzero target temporary/snapshot purposes require separate native accounting')
                observations.append(self.destination.resource_observation(bundle,receipt,observation))
            else:
                require(self.source is not None and pool.scope==self.source.enrollment.scope and pool.inputs is None,
                        'A selected retained source pool lacks its concrete independently enrolled native reader')
                observations.append(self.source.observe_resource(bundle,pool,receipt['reservation_id'],sources))
        return self.resources.confirm(bundle,tuple(observations))
