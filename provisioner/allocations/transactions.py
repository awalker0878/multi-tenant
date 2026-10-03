"""Job-bound live resource transactions over the existing capacity owner.

This owner composes budget purposes, leases and observed native occupancy. It
does not create a second allocation database, infer that a timeout cleaned up a
resource, or execute a native workload. The control-plane verifier must lock
and recheck current admission and the protected execution selection on every
effect. Independent evidence verification remains a required, failing port.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from typing import Protocol

from provisioner.allocations import capacity_owner as owner
from provisioner.allocations import capacity_demand
from provisioner.controlplane.authority.model import PlanScope
from provisioner.controlplane.workflow.admitted_job import AdmittedInput
from provisioner.execution import readback_core as c
from provisioner.execution.run_files import require


@dataclass(frozen=True)
class ResourceUnits:
    vcpu: int = 0
    memory_mb: int = 0
    storage_gb: int = 0

    def __post_init__(self):
        owner.units(asdict(self))

    @classmethod
    def from_bytes(cls, *, vcpu=0, memory_bytes=0, storage_bytes=0):
        """Charge decimal owner units upward, including temporary footprint."""
        require(all(type(n) is int and 0<=n<=10**24 for n in
                    (memory_bytes, storage_bytes)), 'Bounded integral resource bytes required')
        return cls(vcpu, (memory_bytes+10**6-1)//10**6,
                   (storage_bytes+10**9-1)//10**9)


@dataclass(frozen=True)
class PoolDemand:
    scope: PlanScope
    catalog_json: str
    inputs_json: str | None
    envelope_sha256: str
    capabilities: tuple[str, ...]
    staging: ResourceUnits
    snapshots: ResourceUnits
    retained_source: ResourceUnits
    environment_key: str

    @classmethod
    def from_workload(cls, *, scope: PlanScope, catalog: dict,
                      inputs: dict | None, envelope_sha256: str,
                      budgets: dict[str, dict], capabilities: tuple[str, ...],
                      environment_key: str | None = None):
        c.exact_keys(budgets, {'staging', 'snapshots', 'retained-source'})
        # Serializing at the trusted boundary prevents a mutable caller-owned
        # dictionary from changing after the request's digest was reviewed.
        from provisioner.execution.run_files import encoded
        return cls(scope, encoded(catalog).decode(),
                   encoded(inputs).decode() if inputs is not None else None,
                   envelope_sha256, capabilities,
                   ResourceUnits(**budgets['staging']),
                   ResourceUnits(**budgets['snapshots']),
                   ResourceUnits(**budgets['retained-source']),
                   environment_key or (inputs or {}).get('environment_key'))

    def __post_init__(self):
        require(isinstance(self.scope, PlanScope), 'Exact native resource scope required')
        c.identifier(self.environment_key)
        require(isinstance(self.envelope_sha256, str) and c.HEX.fullmatch(self.envelope_sha256),
                'Reviewed commissioned envelope digest required')
        require(isinstance(self.capabilities, tuple) and self.capabilities
                and len(set(self.capabilities))==len(self.capabilities),
                'Exact resource capability set required')
        for capability in self.capabilities: c.identifier(capability)
        require(all(isinstance(budget, ResourceUnits) for budget in
                    (self.staging, self.snapshots, self.retained_source)),
                'Typed explicit temporary and retained-source budgets required')
        catalog=self.catalog
        # Historical readability is independent from current admission.
        capacity_demand.validate_catalog(catalog, current=False)
        require((catalog['site_key'],catalog['platform'],catalog['native_id'])==
                (self.scope.site_id,self.scope.platform_family,self.scope.native_scope_id),
                'Sizing belongs to another native site/platform/pool scope')
        if self.inputs is not None:
            self.demand(current=False)
        require(any(self.total(current=False).values()), 'Empty resource selection is unsupported')

    @property
    def catalog(self):
        return c.strict_loads(self.catalog_json)

    @property
    def inputs(self):
        return c.strict_loads(self.inputs_json) if self.inputs_json is not None else None

    def demand(self, *, current=True):
        catalog=self.catalog
        capacity_demand.validate_catalog(catalog, current=current)
        inputs=self.inputs
        if inputs is None:
            return {'format':'hosting-capacity-demand/1',
                    'scope':{'environment_key':self.environment_key,
                             'site_key':self.scope.site_id,'platform':self.scope.platform_family,
                             'tenant_key':self.scope.tenant_id,'wsd_key':self.scope.security_domain_id},
                    'pool_id':catalog['pool_id'],'sizing_sha256':c.digest(catalog),
                    'units':asdict(ResourceUnits()),'members':{}}
        demand=capacity_demand.derive(inputs,catalog,current=current)
        require((demand['scope']['environment_key'],demand['scope']['site_key'],demand['scope']['platform'],
                 demand['scope']['tenant_key'],demand['scope']['wsd_key'])==
                (self.environment_key,self.scope.site_id,self.scope.platform_family,self.scope.tenant_id,
                 self.scope.security_domain_id), 'Workload demand differs from exact native scope')
        return demand

    def components(self, *, current=True):
        return {'workload':self.demand(current=current)['units'],
                'staging':asdict(self.staging),'snapshots':asdict(self.snapshots),
                'retained-source':asdict(self.retained_source)}

    def total(self, *, current=True):
        components=self.components(current=current)
        total={key:sum(value[key] for value in components.values()) for key in owner.UNITS}
        owner.units(total)
        return total

    def document(self):
        return {'scope':asdict(self.scope),'catalog':self.catalog,'inputs':self.inputs,
                'envelope_sha256':self.envelope_sha256,'environment_key':self.environment_key,
                'capabilities':list(self.capabilities),
                'components':self.components(current=False)}


@dataclass(frozen=True)
class ResourceBundle:
    admitted: AdmittedInput
    selection_digest: str
    workload_id: str
    workload_revision: int
    pools: tuple[PoolDemand, ...]

    def __post_init__(self):
        require(isinstance(self.admitted, AdmittedInput), 'Immutable admitted job required')
        c.identifier(self.workload_id)
        require(type(self.workload_revision) is int and self.workload_revision>0,
                'Exact workload revision required')
        require(isinstance(self.selection_digest,str) and c.HEX.fullmatch(self.selection_digest),
                'Protected execution selection digest required')
        require(isinstance(self.pools,tuple) and 1<=len(self.pools)<=20
                and all(isinstance(pool,PoolDemand) for pool in self.pools),
                'Bounded typed resource pool selection required')
        require(len({(pool.catalog['pool_id'],pool.scope) for pool in self.pools})==len(self.pools),
                'Combine resource purposes before charging one native pool')
        for pool in self.pools:
            require((pool.scope.organization_id,pool.scope.tenant_id)==
                    (self.admitted.organization_id,self.admitted.tenant_id),
                    'Resource selection belongs to another admitted tenant')

    def document(self):
        # Plan -> execution artifact -> this selection must be acyclic.
        # Actual receipts add immutable admitted job/plan/epoch independently.
        return {'format':'hosting-resource-selection/1','workload_id':self.workload_id,
                'workload_revision':self.workload_revision,
                'pools':[pool.document() for pool in self.pools]}

    @property
    def digest(self):
        return c.digest(self.document())

    def requests(self, owner_id: str, *, current=True):
        requests=[]
        for pool in self.pools:
            native_key=c.digest([asdict(pool.scope),pool.catalog['pool_id']])
            identity=c.digest([self.admitted.job_id,native_key])[:40]
            demand=pool.demand(current=current)
            scope=demand['scope']
            request={'format':'hosting-capacity-request/2','owner_id':owner_id,
                     'reservation_id':'resource-'+identity,'operation_id':'resources-'+identity,
                     'generation':self.admitted.plan_revision,'scope':scope,
                     'pool_id':pool.catalog['pool_id'],'units':pool.total(current=current),
                     'capabilities':list(pool.capabilities),'resource_binding':{
                         'job':asdict(self.admitted),'native_scope':asdict(pool.scope),
                         'envelope_sha256':pool.envelope_sha256,
                         'sizing_sha256':c.digest(pool.catalog),'demand_sha256':c.digest(demand),
                         'components':pool.components(current=current),
                         'request_set_sha256':self.digest}}
            owner.validate_owner_request(request)
            requests.append(request)
        return tuple(requests)


@dataclass(frozen=True)
class ResourceObservation:
    """Independent observation reference; construction alone grants no authority.

    The evidence verifier must re-read native state, operation uncertainty and
    old-worker exclusion. UNKNOWN/IN_PROGRESS always retain the owner's charge.
    A release observation covers every previously confirmed resource and the
    temporary/snapshot/retention cleanup, rather than one absent VM lookup.
    """
    reservation_id: str
    evidence_digest: str
    native_ids: tuple[str, ...]
    units: ResourceUnits
    outcome: str  # EFFECT_PRESENT, NO_EFFECT, UNKNOWN, IN_PROGRESS
    observed_at: datetime

    def __post_init__(self):
        c.identifier(self.reservation_id)
        require(isinstance(self.evidence_digest,str) and c.HEX.fullmatch(self.evidence_digest),
                'Independent resource evidence digest required')
        require(isinstance(self.native_ids,tuple) and len(self.native_ids)==len(set(self.native_ids)),
                'Exact unique observed native resources required')
        for value in self.native_ids: c.text(value)
        require(isinstance(self.units,ResourceUnits) and self.outcome in
                {'EFFECT_PRESENT','NO_EFFECT','UNKNOWN','IN_PROGRESS'},
                'Typed resource outcome and measured units required')
        require(isinstance(self.observed_at,datetime) and self.observed_at.tzinfo is not None,
                'Timezone-aware native observation required')


@dataclass(frozen=True)
class ResourceAuthorityWindow:
    source: PlanScope
    destination: PlanScope
    valid_from: datetime
    valid_until: datetime
    evidence_digest: str


class ResourceAuthority(Protocol):
    def locked(self, bundle: ResourceBundle, action: str, observations: tuple):
        """Context manager: independently verify exact persisted selection/epochs.

        Lock/recheck current authority through the short owner transaction;
        additionally revalidate all native observations for confirm/release.
        Returning a boolean or deserializing a caller's authority value is invalid.
        """


class ResourceTransactions:
    def __init__(self, database, authority: ResourceAuthority, *,
                 clock=lambda: datetime.now(timezone.utc)):
        require(callable(getattr(authority,'locked',None)),
                'Live admitted-job and independent evidence verifier required')
        self.database=database
        self.authority=authority
        require(callable(clock),'Resource readiness clock required')
        self._clock=clock

    @staticmethod
    def _observations(requests, observations, action, at):
        require(isinstance(observations,tuple) and all(isinstance(obs,ResourceObservation)
                    for obs in observations), 'Typed independently verified observations required')
        require({obs.reservation_id for obs in observations}==
                {request['reservation_id'] for request in requests}
                and len(observations)==len(requests),
                'Every selected resource pool needs exactly one native observation')
        for obs in observations:
            require(at-timedelta(minutes=5)<=obs.observed_at<=at,
                    'Reobserve resource occupancy and cleanup before transition')
            require(obs.outcome==('EFFECT_PRESENT' if action=='confirm' else 'NO_EFFECT'),
                    'Native effect or cleanup remains uncertain; keep resource charges')
            if action=='confirm':
                require(obs.native_ids,'Native identities are required before confirmation')
            else:
                require(asdict(obs.units)==asdict(ResourceUnits()),
                        'Cleanup still consumes selected resource capacity')
        return {obs.reservation_id:obs for obs in observations}

    def _run(self, bundle, action, observations=()):
        require(isinstance(bundle,ResourceBundle), 'Exact admitted resource bundle required')
        require(action in {'reserve','renew','confirm','release','inspect'},
                'Unknown resource transaction')
        require((bool(observations))==(action in {'confirm','release'}),
                'Native observations are required exactly for confirmation and release')
        # The PostgreSQL authority context outlives the SQLite transaction;
        # revoked epochs serialize with its lock and cannot become fresh grants.
        with self.authority.locked(bundle,action,observations) as window:
            require(isinstance(window,ResourceAuthorityWindow),
                    'Resource verifier did not return its trusted authority window')
            require(window.valid_from.tzinfo is not None and window.valid_until.tzinfo is not None
                    and window.valid_from<window.valid_until<=window.valid_from+timedelta(hours=1)
                    and c.HEX.fullmatch(window.evidence_digest),
                    'Bounded verified resource authority required')
            for pool in bundle.pools:
                require(pool.scope in (window.source,window.destination),
                        'Resource native scope is not selected by the admitted plan')
            with owner.database(self.database) as db:
                owner.verify_events(db)
                envelope=c.strict_loads(db.execute('SELECT body FROM envelope WHERE singleton=1').fetchone()[0])
                requests=bundle.requests(envelope['owner_id'],current=action not in {'release','inspect'})
                observed=(self._observations(requests,observations,action,window.valid_from)
                          if observations else {})
                receipts=[]
                for pool,request in zip(bundle.pools,requests):
                    existing=db.execute('SELECT receipt FROM reservation WHERE id=?',
                                        (request['reservation_id'],)).fetchone()
                    previous=c.strict_loads(existing[0]) if existing else None
                    if action=='inspect':
                        receipts.append(owner._operate_in_database(db,request,'inspect',None,resource=True))
                        continue
                    owner.validate_envelope(envelope,current=action!='release')
                    require(action in {'confirm','release'} or c.digest(envelope)==pool.envelope_sha256,
                            'Commissioned envelope changed; re-review resource selection')
                    native_pool=envelope['pools'][request['pool_id']]
                    require(all(native_pool[key]==pool.catalog[key] for key in
                                ('origin','native_id','platform','site_key')),
                            'Sizing belongs to another authoritative native capacity pool')
                    obs=observed.get(request['reservation_id'])
                    native=[]
                    if action=='confirm':
                        require(all(asdict(obs.units)[key]<=request['units'][key] for key in owner.UNITS),
                                'Observed native occupancy exceeds the reserved resource budgets')
                        minimum={key:request['resource_binding']['components']['workload'][key]+
                                 request['resource_binding']['components']['retained-source'][key]
                                 for key in owner.UNITS}
                        require(all(asdict(obs.units)[key]>=minimum[key] for key in owner.UNITS),
                                'Observed resources do not cover the selected workload/retained-source footprint')
                        native=sorted(obs.native_ids)
                    elif action=='release':
                        require(previous is not None and set(previous['native_ids'])<=set(obs.native_ids),
                                'Cleanup does not cover every confirmed native identity')
                    authority={'format':'hosting-capacity-authority/1',
                               'request_sha256':c.digest(request),'action':action,
                               'native_ids_sha256':c.digest(native),'envelope_sha256':c.digest(envelope),
                               'previous_receipt_sha256':c.digest(previous) if previous else None,
                               'valid_from':window.valid_from.isoformat(),
                               'valid_until':window.valid_until.isoformat(),
                               'change_ref':'job:'+bundle.admitted.job_id,
                               'evidence_ref':obs.evidence_digest if obs else window.evidence_digest}
                    receipts.append(owner._operate_in_database(db,request,action,authority,native,resource=True))
                return {'format':'hosting-resource-transaction/1','job':asdict(bundle.admitted),
                        'selection_sha256':bundle.selection_digest,'resource_bundle_sha256':bundle.digest,
                        'action':action,'receipts':receipts,
                        'native_acceptance':False,'production_activation':False}

    def reserve(self,bundle):
        return self._run(bundle,'reserve')

    def renew(self,bundle):
        return self._run(bundle,'renew')

    def confirm(self,bundle,observations):
        return self._run(bundle,'confirm',observations)

    def release(self,bundle,observations):
        return self._run(bundle,'release',observations)

    def inspect(self,bundle):
        return self._run(bundle,'inspect')

    def require_ready(self,bundle):
        result=self.inspect(bundle)
        return self._require_accounted(bundle,result)

    def _require_accounted(self,bundle,result=None):
        """Read accounting inside a caller's already-verified PG grant context.

        This private method grants no plan/job authority. Planned native-lease
        lookup calls it after locking the same current job and approvals, which
        avoids opening a second PostgreSQL transaction on those held locks.
        """
        require(isinstance(bundle,ResourceBundle),'Exact resource selection required')
        at=self._clock()
        with owner.database(self.database) as db:
            owner.verify_events(db)
            envelope=c.strict_loads(db.execute('SELECT body FROM envelope WHERE singleton=1').fetchone()[0])
            owner.validate_envelope(envelope)
            requests=bundle.requests(envelope['owner_id'])
            receipts=[]
            for number,(pool,request) in enumerate(zip(bundle.pools,requests)):
                current=db.execute('SELECT receipt FROM reservation WHERE id=?',
                                   (request['reservation_id'],)).fetchone()
                require(current is not None,'Resource selection is not reserved by its owner')
                receipt=c.strict_loads(current[0])
                require(result is None or result['receipts'][number]==receipt,
                        'Resource receipt changed during readiness observation')
                require(c.digest(envelope)==pool.envelope_sha256,
                        'Current commissioned envelope differs from resource admission')
                require(receipt['request_sha256']==c.digest(request) and receipt['status'] in owner.LIVE,
                        'Resource transaction is no longer live')
                if receipt['status']=='RESERVED':
                    require(c.timestamp(receipt['lease_expires_at'])>at,
                            'Speculative resource hold expired; reauthorize and renew without releasing it')
                receipts.append(receipt)
        return result if result is not None else {
            'format':'hosting-resource-transaction/1','job':asdict(bundle.admitted),
            'selection_sha256':bundle.selection_digest,'resource_bundle_sha256':bundle.digest,
            'action':'inspect','receipts':receipts,
            'native_acceptance':False,'production_activation':False}
