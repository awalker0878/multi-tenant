"""Fresh project-read credentials for the selected Terraform planning owner.

The Vault dynamic role and Keystone project-reader policy must be independently
commissioned. Native role names are checked on an actual authenticated token;
they are not inferred from a scope label or a signed credential JSON envelope.
"""
from __future__ import annotations

from dataclasses import dataclass
import http.client
from pathlib import Path
import ssl
from urllib.parse import urlsplit
from uuid import uuid4

from provisioner.controlplane.reconciliation.planned_terraform import (
    VaultOpenStackCredentialConsumer, _cloud_projection)
from provisioner.controlplane.worker.grants import CredentialBroker
from provisioner.execution import delivery_steps, readback_core as c, terraform_run
from provisioner.execution.neutron_observe import strict_loads
from provisioner.execution.run_files import (
    digest, encoded, load_private, private_path, read_private,
    require, sync_directory, utcnow, write_new)
from ..command_runtime import WorkerCommandRuntime, SelectedWorkerCommandAuthority


@dataclass(frozen=True)
class ScopedOpenStackPlanningRuntime:
    command_runtime: WorkerCommandRuntime
    broker: CredentialBroker
    consumer: VaultOpenStackCredentialConsumer
    readonly_role_names: tuple[str, ...]
    compute_origin: str

    def __post_init__(self):
        require(isinstance(self.command_runtime, WorkerCommandRuntime)
                and isinstance(self.broker, CredentialBroker)
                and isinstance(self.consumer, VaultOpenStackCredentialConsumer)
                and self.broker._identities is self.command_runtime.verifier
                and self.broker._grants is self.command_runtime.grants
                and self.broker._issuer is self.consumer.issuer
                and self.command_runtime.grant.operation_kind == 'DISCOVER_READ'
                and self.command_runtime.grant.operation_scope.platform_family == 'openstack',
                'A separately enrolled actual project-read grant and Vault issuer required')
        # The selected native policy uses the standard project reader role.
        # Another role profile needs a separately implemented/qualified owner.
        require(self.readonly_role_names == ('reader',)
                and c.origin(self.compute_origin) == self.compute_origin,
                'The commissioned project-reader role and exact compute origin are required')
        roles = tuple(role for role in self.consumer.issuer._roles.values()
                      if role.scope == self.command_runtime.grant.operation_scope
                      and role.operation_kind == 'DISCOVER_READ')
        require(len(roles) == 1, 'One fixed scoped dynamic project-read role is required')

    def run_step(self, admitted, selection, plan, step, packet, directory, base, root, *, guard=None):
        require(step['kind'] == 'terraform_plan', 'This credential owner only prepares the selected plan')
        authority = self.command_runtime.select(admitted, selection, plan, step, packet, root,
                                                intent_guard=guard)
        files, values = delivery_steps.file_paths(packet), packet['parameters']
        from argparse import Namespace
        args = Namespace(catalog_id=values['catalog_id'], terraform=Path(values['terraform']),
            inputs=files['inputs'], backend=files['backend'], authority=files['authority'],
            environment=files['environment'], cloud=files.get('cloud'),
            ca_bundle=files.get('ca_bundle'), references=files.get('references'),
            transition=files.get('transition'), output=directory/'execution', read_authorized_target=True)
        context = EphemeralOpenStackPlanningContext(self, authority)
        result = terraform_run.prepare(args, root=root, planning_context=context)
        authority.require_current()
        for name in ('bundle.json', 'review.json'):
            write_new(directory/name, read_private(directory/'execution'/name))
        return delivery_steps.complete(step, packet, directory, plan, result, ['bundle.json', 'review.json'])


class EphemeralOpenStackPlanningContext:
    """In-memory binding reused only by one concrete Terraform preparation.

    Fresh native/backend secrets are consumed for each individual subprocess
    and removed afterwards. Original reviewed bytes are retained for audit;
    they are never the selected application's command credential source.
    """
    def __init__(self, runtime, authority):
        require(isinstance(runtime, ScopedOpenStackPlanningRuntime)
                and isinstance(authority, SelectedWorkerCommandAuthority)
                and authority.runtime is runtime.command_runtime
                and authority.step['kind'] == 'terraform_plan',
                'Concrete selected project-read planning context required')
        self.runtime, self.authority = runtime, authority
        self.binding = None
        self.commands = []
        self.runtime_assets = None

    def bind_prepare(self, args, entry, scope, credentials, cloud, ca_bytes):
        grant, _deadline = self.authority.require_current()
        require(self.binding is None and entry['platform'] == 'openstack'
                and scope == self.authority.selection['executionScope'] | {'phase': entry['root'].split('/')[-1]}
                and scope['phase'] == 'workloads'
                and grant.operation_scope == grant.destination
                and 'TF_VAR_platform_password' not in credentials and cloud is not None,
                'Only the selected project-read workload planning purpose is supported')
        values = self.authority.packet['parameters']
        require(entry['id'] == values['catalog_id']
                and Path(args.terraform).resolve(strict=True) == Path(values['terraform']).resolve(strict=True)
                and digest(Path(args.terraform).read_bytes()) == values['terraform_sha256'],
                'The exact selected Terraform composition or executable changed')
        self.alias = load_private(args.inputs)['openstack_cloud']
        self.original_cloud = _cloud_projection(cloud, self.alias)
        self.environment_keys = frozenset(credentials)
        self.ca_bytes = ca_bytes
        self.binding = (entry['root'], dict(scope), Path(args.output).absolute())
        self.binary = Path(args.terraform).resolve(strict=True)
        self.binary_digest = values['terraform_sha256']

    def _native_identity(self, cloud, expires):
        selected = cloud['clouds'][self.alias]
        parsed = urlsplit(selected['auth']['auth_url'])
        require(parsed.path.rstrip('/') == '/v3', 'Exact Keystone v3 identity authority required')
        tls = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        tls.minimum_version = ssl.TLSVersion.TLSv1_2
        tls.verify_flags |= ssl.VERIFY_X509_STRICT
        if self.ca_bytes is None:
            tls.load_default_certs(ssl.Purpose.SERVER_AUTH)
        else:
            tls.load_verify_locations(cadata=self.ca_bytes.decode('ascii'))
        seconds = min(10, (expires - utcnow()).total_seconds())
        require(seconds > 0, 'The native read credential expired before authentication')
        connection = http.client.HTTPSConnection(parsed.hostname, parsed.port or 443,
                                                 timeout=seconds, context=tls)
        body = {'auth': {'identity': {'methods': ['application_credential'], 'application_credential': {
            'id': selected['auth']['application_credential_id'],
            'secret': selected['auth']['application_credential_secret']}}}}
        try:
            connection.request('POST', '/v3/auth/tokens', body=encoded(body),
                headers={'Accept': 'application/json', 'Content-Type': 'application/json'})
            response = connection.getresponse(); raw = response.read(262145)
            require(response.status == 201 and len(raw) <= 262144
                    and response.headers.get_content_type() == 'application/json'
                    and bool(response.getheader('X-Subject-Token')),
                    'Actual Keystone authentication refused the bounded read identity')
            payload = strict_loads(raw)
            token = payload.get('token') if type(payload) is dict else None
            require(type(token) is dict and token.get('methods') == ['application_credential']
                    and token.get('project', {}).get('id') == self.runtime.command_runtime.grant.operation_scope.native_scope_id
                    and token.get('application_credential', {}).get('id') == selected['auth']['application_credential_id']
                    and token.get('system') is None and token.get('domain') is None
                    and type(token.get('roles')) is list and token['roles']
                    and all(type(role) is dict and type(role.get('name')) is str for role in token['roles'])
                    and {role['name'] for role in token['roles']} == set(self.runtime.readonly_role_names)
                    and type(token.get('catalog')) is list,
                    'Fresh native identity is not the exact project-reader credential')
            endpoints = [endpoint for service in token['catalog']
                if type(service) is dict and service.get('type') == 'compute'
                and type(service.get('endpoints')) is list for endpoint in service['endpoints']
                if type(endpoint) is dict and endpoint.get('interface') == selected['interface']
                and endpoint.get('region') == selected['region_name']]
            endpoint = urlsplit(endpoints[0]['url']) if len(endpoints) == 1 else None
            require(endpoint is not None and endpoint.scheme == 'https' and endpoint.hostname
                    and not endpoint.username and not endpoint.password and not endpoint.query and not endpoint.fragment
                    and c.origin(f'{endpoint.scheme}://{endpoint.netloc}') == self.runtime.compute_origin,
                    'Fresh compute catalogue differs from the commissioned project-read endpoint')
            native_expires = c.timestamp(token['expires_at'])
            require(native_expires > utcnow(), 'The actual project-read token expired')
            return min(expires, native_expires)
        finally:
            connection.close()

    def execute_command(self, contact, binary, directory, argv, _environment, output, **keywords):
        require(self.binding is not None and isinstance(directory, Path) and len(self.commands) < 4,
                'The original planning context cannot change or replay its command sequence')
        operation = private_path(self.binding[2], directory=True)
        sequence = (
            (['version','-json'],'version.json'),
            (['init','-input=false','-no-color','-lockfile=readonly','-reconfigure',
              '-backend-config='+str(operation/'backend.hcl')],'init.log'),
            (['plan','-input=false','-no-color','-lock=true','-lock-timeout=60s','-detailed-exitcode',
              '-var-file='+str(operation/'inputs.json'),'-out='+str(operation/'saved.tfplan')],'plan.log'),
            (['show','-json',str(operation/'saved.tfplan')],'plan.json'))
        expected, name = sequence[len(self.commands)]
        require(list(argv) == expected and output == operation/name
                and directory == operation/'source'/self.binding[0]
                and Path(binary).resolve(strict=True) == self.binary and self.binary.is_file()
                and digest(self.binary.read_bytes()) == self.binary_digest,
                'The original planning command changed its executable, exact arguments or output purpose')
        assets = {path.relative_to(operation).as_posix():digest(read_private(path))
                  for path in (operation/'source').rglob('*')
                  if path.is_file() and '.terraform' not in path.relative_to(operation/'source').parts}
        for name in ('inputs.json','backend.json','backend.hcl','contact.json','references.json',
                     'transition.json','terraform.rc','ca.pem'):
            if (operation/name).exists(): assets[name] = digest(read_private(operation/name))
        if self.runtime_assets is None: self.runtime_assets = assets
        require(assets == self.runtime_assets
                and ((operation/'ca.pem').exists() == (self.ca_bytes is not None))
                and (self.ca_bytes is None or read_private(operation/'ca.pem') == self.ca_bytes),
                'The original prepared source, inputs, backend or trust files changed between planning commands')
        self.authority.require_current()
        runtime = self.runtime.command_runtime
        grant, deadline = self.authority.require_current()
        handle = self.runtime.broker.acquire(runtime.transport_evidence, runtime.context, grant.grant_id,
                                            **runtime.grant_arguments(self.authority.admitted))
        data, expires, _lease_digest = self.runtime.consumer.unwrap(handle, grant)
        cloud = terraform_run.cloud_config(encoded(data['cloud']), self.alias)
        require(_cloud_projection(cloud, self.alias) == self.original_cloud
                and frozenset(data['environment']) == self.environment_keys,
                'Fresh read credentials changed the reviewed endpoint or backend environment projection')
        expires = self._native_identity(cloud, min(expires, deadline))
        self.authority.require_current()
        secrets = operation/('read-auth-' + uuid4().hex)
        secrets.mkdir(mode=0o700); sync_directory(operation)
        path = secrets/'clouds.yaml'
        profile = {'clouds': {self.alias: dict(cloud['clouds'][self.alias])}}
        if self.ca_bytes is not None:
            profile['clouds'][self.alias]['cacert'] = str(operation/'ca.pem')
        try:
            write_new(path, encoded(profile))
            env = terraform_run.runtime_environment(operation, data['environment'], 'openstack', directory)
            env['OS_CLIENT_CONFIG_FILE'] = str(path)
            remaining = min(self.authority.timeout(keywords.get('timeout', 900)),
                            (expires - utcnow()).total_seconds())
            require(remaining > 0, 'The next planning command has no remaining credential lease')
            self.commands.append(argv[0])
            result = terraform_run.command(binary, directory, argv, env, output,
                                            **(keywords | {'timeout': remaining}))
            self.authority.require_current()
            return result
        finally:
            path.unlink(missing_ok=True); secrets.rmdir(); sync_directory(operation)
