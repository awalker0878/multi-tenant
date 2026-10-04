"""One enrolled OpenStack deployment through the saved-plan and B10/B11 owners.

The approved plan, source, inputs and provider endpoint remain immutable. A
current Vault dynamic role may refresh only its secrets. The fresh identity is
authenticated against the retained Keystone authority and exact native project
before the one existing creation intent can be claimed. No API task identifier
is derived from Terraform's exit code or output file.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import http.client
import ssl
from urllib.parse import urlsplit
from uuid import uuid4

from provisioner.allocations.transactions import ResourceBundle
from provisioner.controlplane.authority.model import WorkerGrant
from provisioner.controlplane.jobs.repository import _digest
from provisioner.controlplane.persistence import TenantContext
from provisioner.controlplane.worker.grants import (
    CredentialBroker, GrantDenied, PostgresWorkerGrants, VerifiedWorkerIdentity)
from provisioner.controlplane.worker.pki import MutualTlsWorkerVerifier
from provisioner.controlplane.worker.vault import VaultDynamicCredentialIssuer, VaultWrappedCredential
from provisioner.controlplane.workflow.admitted_job import AdmittedInput
from provisioner.controlplane.workflow.execution_selection import PostgresExecutionAuthority
from provisioner.execution import delivery_steps, readback_core as c
from provisioner.execution.neutron_observe import strict_loads
from provisioner.execution.run_files import (
    digest, encoded, load_private, private_path, read_private, require, sync_directory, write_new)
from provisioner.execution.terraform_apply import validate_bundle
from provisioner.execution.terraform_run import cloud_config, process_environment, runtime_environment
from .planned import (
    NativeCreationObservation, PlannedNativeCreationRegistry, PlannedResourceLease,
    creation_children, require_creation_inputs)
from .registry import OperationConflict, RecoveryHeld


def _now():
    return datetime.now(timezone.utc)


def _cloud_projection(cloud, alias):
    selected=cloud['clouds'][alias]
    return {'cloud':alias,'auth_type':selected['auth_type'],
            'auth_url':selected['auth']['auth_url'],'region_name':selected['region_name'],
            'interface':selected['interface'],'verify':selected['verify']}


class VaultOpenStackCredentialConsumer:
    """Unwrap once at the issuer's pinned HTTPS endpoint, without an agent token.

    The independently enrolled dynamic role must issue a revocable Vault lease
    whose data is exactly ``environment`` and ``cloud``. Its native credential
    and backend permissions are constrained by that role's deployment policy.
    Missing or incompatible role payloads stop before native creation.
    """
    def __init__(self, issuer: VaultDynamicCredentialIssuer):
        if not isinstance(issuer,VaultDynamicCredentialIssuer):
            raise TypeError('The concrete enrolled Vault dynamic credential issuer is required')
        self.issuer=issuer

    def unwrap(self, handle: VaultWrappedCredential, grant: WorkerGrant):
        now=_now()
        if (not isinstance(handle,VaultWrappedCredential) or not isinstance(grant,WorkerGrant)
                or handle.grant_id!=grant.grant_id or handle.expires_at<=now
                or handle.expires_at>grant.expires_at):
            raise GrantDenied('Exact current single-use credential and creation grant required')
        roles=[role for role in self.issuer._roles.values()
               if handle.creation_path in (role.api_path,'/v1/'+role.api_path)]
        if (len(roles)!=1 or roles[0].scope!=grant.operation_scope
                or roles[0].operation_kind!=grant.operation_kind):
            raise GrantDenied('Wrapped credential belongs to another enrolled dynamic role')
        headers={'X-Vault-Token':handle.wrapping_token,'X-Vault-Request':'true',
                 'Accept':'application/json','Content-Type':'application/json'}
        if self.issuer._namespace is not None:
            headers['X-Vault-Namespace']=self.issuer._namespace
        connection=http.client.HTTPSConnection(self.issuer._host,self.issuer._port,
            timeout=min(self.issuer._timeout,(handle.expires_at-now).total_seconds()),context=self.issuer._tls)
        try:
            connection.request('POST','/v1/sys/wrapping/unwrap',body=b'{}',headers=headers)
            response=connection.getresponse(); raw=response.read(65537)
            if (response.status!=200 or len(raw)>65536
                    or response.headers.get_content_type()!='application/json'):
                raise GrantDenied('Vault refused bounded single-use credential consumption')
            payload=strict_loads(raw)
            seconds=payload.get('lease_duration') if type(payload) is dict else None
            lease_id=payload.get('lease_id') if type(payload) is dict else None
            data=payload.get('data') if type(payload) is dict else None
            if (not isinstance(lease_id,str) or not lease_id or len(lease_id)>4096
                    or type(seconds) is not int or not 0<seconds<=int(roles[0].max_credential_ttl.total_seconds())
                    or type(data) is not dict or data.keys()!={'environment','cloud'}
                    or payload.get('auth') is not None or payload.get('wrap_info') is not None):
                raise GrantDenied('Dynamic role must return one bounded native/backend lease')
            process_environment(data['environment'])
            expiry=min(handle.expires_at,grant.expires_at,_now()+timedelta(seconds=seconds))
            if self.issuer._lease_store is not None:
                self.issuer._lease_store.consumed(handle,grant,lease_id,expiry)
            return data,expiry,digest(lease_id.encode())
        except (OSError,TimeoutError,ssl.SSLError,http.client.HTTPException,ValueError,UnicodeError) as exc:
            raise GrantDenied('Ephemeral OpenStack credential consumption failed') from exc
        finally:
            connection.close()


class EphemeralOpenStackApplyContext:
    """Process-local effect authority; never construct it from queue JSON.

    Construction performs live B10 issuance, one-time Vault consumption and
    actual Keystone project/catalog verification. Each subprocess rechecks
    the original job, current grant, selected intent and native identity. The
    existing static CLI apply path continues to verify its historical secrets.
    """
    def __init__(self, runtime, admitted, selection, bundle, prepared, saved):
        if not isinstance(runtime,PlannedTerraformRuntime):
            raise TypeError('Only the concrete enrolled planned Terraform runtime may bind an apply')
        self.runtime,self.admitted,self.selection,self.bundle=runtime,admitted,selection,bundle
        self.prepared,self.saved=private_path(prepared,directory=True),saved
        self.bundle_digest=digest(read_private(self.prepared/'bundle.json'))
        self.inputs=load_private(self.prepared/'inputs.json')
        require_creation_inputs(bundle,runtime.lease.scope,runtime.lease.resource_id,self.inputs)
        require(saved['scope']==selection['executionScope']|{'phase':'workloads'},
                'Only the exact selected workload deployment has this creation authority')
        self.pool=next(pool for pool in bundle.pools if pool.scope==runtime.lease.scope and pool.inputs is not None)
        self.alias=self.inputs['openstack_cloud']
        old=load_private(self.prepared/'source'/saved['root']/'clouds.yaml')
        # The prepared source adds only this exact private CA path to the cloud.
        self.ca_path=self.prepared/'ca.pem' if 'ca.pem' in saved['artifacts'] else None
        original={'clouds':{self.alias:dict(old['clouds'][self.alias])}}
        if self.ca_path is not None:
            require(original['clouds'][self.alias].pop('cacert',None)==str(self.ca_path),
                    'Prepared native trust path differs from the reviewed bundle')
        old=cloud_config(encoded(original),self.alias)
        require(load_private(self.prepared/'contact.json')['cloud_sha256']==self.pool.catalog['cloud_sha256'],
                'Saved cloud configuration differs from the commissioned capacity catalogue')
        handle=runtime.broker.acquire(runtime.transport_evidence,runtime.context,runtime.grant.grant_id,
                                      **runtime.grant_arguments())
        data,expires,self.native_lease_digest=runtime.consumer.unwrap(handle,runtime.grant)
        self.expires_at=min(expires,runtime.lease.expires_at)
        fresh=cloud_config(encoded(data['cloud']),self.alias)
        require(_cloud_projection(old,self.alias)==_cloud_projection(fresh,self.alias),
                'Ephemeral secrets cannot change cloud alias, identity authority, region, interface or TLS')
        historical=load_private(self.prepared/'environment.json')
        require(data['environment'].keys()==historical.keys()
                and 'TF_VAR_platform_password' not in historical,
                'Ephemeral backend credentials must preserve the exact OpenStack environment projection')
        self.environment_credentials=data['environment']
        self.cloud=fresh
        self.expires_at=min(self.expires_at,self._authenticate_native())
        folder=self.prepared/'ephemeral-auth'
        if not folder.exists():
            folder.mkdir(mode=0o700); sync_directory(folder.parent)
        private_path(folder,directory=True)
        self.directory=folder/uuid4().hex
        self.directory.mkdir(mode=0o700); sync_directory(folder)
        profile={'clouds':{self.alias:dict(self.cloud['clouds'][self.alias])}}
        if self.ca_path is not None: profile['clouds'][self.alias]['cacert']=str(self.ca_path)
        self.cloud_path=self.directory/'clouds.yaml'
        write_new(self.cloud_path,encoded(profile))
        self.cloud_digest=digest(read_private(self.cloud_path))
        manifest={'format':'hosting-ephemeral-openstack-apply-context/1','bundle_sha256':self.bundle_digest,
            'resource_bundle_sha256':bundle.digest,'grant_id':runtime.grant.grant_id,
            'native_lease_sha256':self.native_lease_digest,'scope':saved['scope'],
            'nonsecret_cloud':_cloud_projection(self.cloud,self.alias),
            'environment_keys':sorted(self.environment_credentials),
            'backend_sha256':saved['artifacts']['backend.json'],
            'ca_sha256':saved['artifacts'].get('ca.pem'),'expires_at':self.expires_at.isoformat()}
        write_new(self.directory/'binding.json',encoded(manifest))

    def _authenticate_native(self):
        """Check actual scoped identity, rather than trusting a scope label."""
        selected=self.cloud['clouds'][self.alias]
        authority=urlsplit(selected['auth']['auth_url'])
        require(authority.path.rstrip('/')=='/v3', 'Exact Keystone v3 authentication authority required')
        tls=ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT); tls.minimum_version=ssl.TLSVersion.TLSv1_2
        tls.verify_flags|=ssl.VERIFY_X509_STRICT
        if self.ca_path is None: tls.load_default_certs(ssl.Purpose.SERVER_AUTH)
        else: tls.load_verify_locations(cafile=str(self.ca_path))
        remaining=min(10,(self.expires_at-_now()).total_seconds())
        require(remaining>0,'Ephemeral creation credential expired before native authentication')
        connection=http.client.HTTPSConnection(authority.hostname,authority.port or 443,
                                               timeout=remaining,context=tls)
        body={'auth':{'identity':{'methods':['application_credential'],'application_credential':{
            'id':selected['auth']['application_credential_id'],
            'secret':selected['auth']['application_credential_secret']}}}}
        try:
            connection.request('POST','/v3/auth/tokens',body=encoded(body),
                headers={'Accept':'application/json','Content-Type':'application/json'})
            response=connection.getresponse(); raw=response.read(262145)
            require(response.status==201 and len(raw)<=262144
                    and response.headers.get_content_type()=='application/json'
                    and bool(response.getheader('X-Subject-Token')),
                    'Native authority refused bounded application-credential authentication')
            payload=strict_loads(raw); token=payload.get('token') if type(payload) is dict else None
            require(type(token) is dict and token.get('project',{}).get('id')==self.runtime.lease.scope.native_scope_id
                    and token.get('application_credential',{}).get('id')==selected['auth']['application_credential_id']
                    and token.get('methods')==['application_credential']
                    and type(token.get('catalog')) is list,
                    'Fresh native identity differs from the enrolled project or application credential')
            endpoints=[]
            for service in token['catalog']:
                if type(service) is dict and service.get('type')=='compute':
                    require(type(service.get('endpoints')) is list,'Bounded native compute catalogue required')
                    endpoints.extend(endpoint for endpoint in service['endpoints'] if type(endpoint) is dict
                        and endpoint.get('interface')==selected['interface']
                        and endpoint.get('region')==selected['region_name'])
            endpoint=urlsplit(endpoints[0]['url']) if len(endpoints)==1 else None
            require(endpoint is not None and endpoint.scheme=='https' and endpoint.hostname
                    and not endpoint.username and not endpoint.password and not endpoint.query and not endpoint.fragment
                    and c.origin(f'{endpoint.scheme}://{endpoint.netloc}')==self.pool.catalog['origin'],
                    'Fresh native compute endpoint differs from the commissioned capacity origin')
            expires=c.timestamp(token['expires_at'])
            require(expires>_now(),'Native application-credential token is expired')
            return expires
        except (OSError,TimeoutError,ssl.SSLError,http.client.HTTPException,ValueError,KeyError,UnicodeError) as exc:
            raise GrantDenied('Exact native project/endpoint credential authentication failed') from exc
        finally:
            connection.close()

    def require_current(self, operation, saved):
        require(private_path(operation,directory=True)==self.prepared
                and saved==self.saved and digest(read_private(operation/'bundle.json'))==self.bundle_digest,
                'A live ephemeral context cannot authorize another saved plan')
        require_creation_inputs(self.bundle,self.runtime.lease.scope,self.runtime.lease.resource_id,
                                load_private(operation/'inputs.json'))
        self.runtime.authority.require_current(self.admitted,self.bundle.selection_digest,'VM_CREATE',
            continuation_grant=self.runtime.grant,continuation_identity=self.runtime.identity)
        # Live mTLS verification is repeated, not retained as a caller claim.
        require(self.runtime.broker._identities.verify(self.runtime.transport_evidence)==self.runtime.identity,
                'The current authenticated worker changed')
        require(self.expires_at>_now(),'Ephemeral native/backend lease expired')
        require(digest(read_private(self.cloud_path))==self.cloud_digest,
                'The process-local ephemeral provider credential binding changed')
        self.expires_at=min(self.expires_at,self._authenticate_native())
        require(self.expires_at>_now(),'Native credential deadline expired during verification')

    def environment(self, operation, directory):
        env=runtime_environment(operation,self.environment_credentials,'openstack',directory)
        env['OS_CLIENT_CONFIG_FILE']=str(self.cloud_path)
        return env

    def remaining_seconds(self):
        return (min(self.expires_at,self.runtime.grant.expires_at)-_now()).total_seconds()

    def acknowledge_completed(self):
        """Verified actual creation must precede a delivery completion marker."""
        observed=self.runtime.observer.observe_creation(self.runtime.context,self.runtime.lease,
            self.runtime.grant.operation_id,self.bundle,self.prepared)
        require(isinstance(observed,NativeCreationObservation)
                and len([binding for binding in observed.bindings if binding.resource_kind=='vm'])==
                len(creation_children(self.bundle,self.runtime.lease.scope,self.runtime.lease.resource_id)),
                'Independent current native readback must cover every selected target VM')
        self.runtime.registry.acknowledge_created(self.runtime.context,self.runtime.lease,
            self.runtime.grant.operation_id,self.runtime.identity,observed)
        self.runtime.retirement.retire(self.runtime,self.admitted,self.selection)
        self.runtime.resource_accounting.confirm_creation(self.runtime,self.admitted,self.selection,self.bundle,observed)


class PlannedTerraformRuntime:
    """Fixed native owner binding, supplied only by authenticated enrollment."""
    def __init__(self, *, context: TenantContext, lease: PlannedResourceLease,
                 registry: PlannedNativeCreationRegistry, grants: PostgresWorkerGrants,
                 identity: VerifiedWorkerIdentity, grant: WorkerGrant,
                 broker: CredentialBroker, transport_evidence,
                 authority: PostgresExecutionAuthority, bundles, observer, resource_accounting=None):
        if (not isinstance(context,TenantContext) or not isinstance(lease,PlannedResourceLease)
                or not isinstance(registry,PlannedNativeCreationRegistry)
                or not isinstance(grants,PostgresWorkerGrants) or registry._grants is not grants
                or grants._leases is not registry.leases
                or not isinstance(identity,VerifiedWorkerIdentity) or not isinstance(grant,WorkerGrant)
                or not isinstance(broker,CredentialBroker) or broker._grants is not grants
                or not isinstance(broker._issuer,VaultDynamicCredentialIssuer)
                or not isinstance(broker._identities,MutualTlsWorkerVerifier)
                or not isinstance(authority,PostgresExecutionAuthority)
                or not callable(bundles) or not callable(getattr(observer,'observe_creation',None))):
            raise TypeError('Concrete enrolled creation owner, live grants, mTLS broker and independent reader required')
        if ((lease.organization_id,lease.tenant_id,lease.worker_id,lease.scope)!=
            (context.organization_id,context.tenant_id,identity.subject,grant.operation_scope)
                or (identity.organization_id,identity.tenant_id,identity.site_id)!=
                   (context.organization_id,context.tenant_id,lease.scope.site_id)
                or grant.worker_subject!=identity.subject or grant.operation_kind!='VM_CREATE'
                or grant.lease_epoch!=lease.epoch or not grant.operation_id or lease.resource_kind!='deployment'):
            raise OperationConflict('Only the exact enrolled aggregate deployment may run this saved plan')
        self.context,self.lease,self.registry,self.grants=context,lease,registry,grants
        self.identity,self.grant,self.broker=identity,grant,broker
        self.transport_evidence,self.authority,self.bundles,self.observer=transport_evidence,authority,bundles,observer
        self.consumer=VaultOpenStackCredentialConsumer(broker._issuer)
        from provisioner.controlplane.worker.native_retirement import CompletedNativeGrantRetirement
        self.retirement=CompletedNativeGrantRetirement(store=broker._issuer._lease_store,
            issuer=broker._issuer,grants=grants)
        from .application_accounting import ApplicationResourceAccounting
        if resource_accounting is None:
            resource_accounting=ApplicationResourceAccounting(resources=registry.leases.resources,destination=observer)
        require(type(resource_accounting) is ApplicationResourceAccounting
                and resource_accounting.resources is registry.leases.resources
                and resource_accounting.destination is observer,
                'Concrete independently enrolled resource accounting must precede target delivery completion')
        self.resource_accounting=resource_accounting

    def grant_arguments(self):
        return {'job_id':self.lease.job_id,'step_id':self.grant.step_id,
            'operation_id':self.grant.operation_id,'operation_kind':'VM_CREATE',
            'operation_scope':self.lease.scope,'lease_key':self.grant.lease_key,'lease_epoch':self.lease.epoch}

    def run_step(self, admitted, selection, delivery, step, packet, directory, base, root):
        if (not isinstance(admitted,AdmittedInput) or admitted.job_id!=self.lease.job_id
                or step['kind']!='terraform_apply' or step['id']!=self.grant.step_id
                or (admitted.organization_id,admitted.tenant_id,admitted.plan_id,admitted.plan_revision,
                    admitted.plan_digest,admitted.revocation_epoch)!=
                   (self.grant.organization_id,self.grant.tenant_id,self.grant.plan_id,
                    self.grant.plan_revision,self.grant.plan_digest,self.grant.revocation_epoch)
                or _digest(selection)!=self.lease.selection_digest):
            raise OperationConflict('Native binding differs from the admitted selected creation step')
        self.authority.require_packet(admitted,self.lease.selection_digest,delivery,step,packet,'VM_CREATE')
        bundle=self.bundles(admitted,selection)
        require(isinstance(bundle,ResourceBundle),'The protected current resource bundle is required')
        prepared=delivery_steps.prepared_directory(step,packet,delivery,base)
        prior=load_private(prepared.parent/'packet.json')['parameters']
        files=delivery_steps.file_paths(packet)
        saved=validate_bundle(prepared,load_private(files['approval']),prior['terraform'],root)
        require_creation_inputs(bundle,self.lease.scope,self.lease.resource_id,load_private(prepared/'inputs.json'))
        operation=self.registry.prepare(self.context,self.lease,grant_id=self.grant.grant_id,
            step_id=self.grant.step_id,lease_key=self.grant.lease_key,
            operation_id=self.grant.operation_id,worker_identity=self.identity)
        if operation.state!='PREPARED':
            raise RecoveryHeld('Creation already claimed; reconcile its existing native intent without redispatch')
        # Credential failure happens before the durable claim and native write.
        apply_context=EphemeralOpenStackApplyContext(self,admitted,selection,bundle,prepared,saved)
        if not self.registry.claim_once(self.context,self.lease,self.grant.operation_id,self.identity):
            raise RecoveryHeld('Creation was claimed concurrently; do not apply again')
        try:
            result=delivery_steps.dispatch(step,packet,directory,base,delivery,root,
                                           openstack_apply_context=apply_context)
            return result
        except BaseException:
            # The persisted claim survives native timeout, failed readback or
            # loss of the coordinator reply; no retry or expiry releases it.
            current=self.registry.get(self.context,self.grant.operation_id)
            if current.state in {'IN_FLIGHT','TASK_ACCEPTED'}:
                self.registry.mark_uncertain(self.context,self.grant.operation_id,self.identity.subject)
            raise
