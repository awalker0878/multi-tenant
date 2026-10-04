"""Fixed Windows Server 2022 identity and service actions, without transport.

An approved descriptor selects concrete existing services and executable bytes.
It cannot contain PowerShell text, a shell command, credentials or a script path.
The current WinRM command owner alone dispatches these source-owned actions.
"""
from dataclasses import dataclass
import base64
import ipaddress
from pathlib import PureWindowsPath
import re
from urllib.parse import urlsplit
from uuid import UUID

from provisioner.controlplane.persistence.store import NativeBinding
from provisioner.execution.neutron_observe import strict_loads
from provisioner.execution.guest_native_profiles import NATIVE_GUEST_PROFILES
from provisioner.execution.run_files import digest, encoded, require

FORMAT = 'hosting-windows-guest-selection/1'
_HASH = re.compile('[0-9a-f]{64}')
_SERVICE = re.compile('[A-Za-z][A-Za-z0-9_.-]{0,127}')
ACTIONS = frozenset({'IDENTITY', 'OBSERVE_SERVICE', 'SET_STARTUP', 'START_SERVICE', 'STOP_SERVICE'})

POWERSHELL = r'''
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
$binding = [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('__BINDING__')) | ConvertFrom-Json
$os = Get-CimInstance -ClassName Win32_OperatingSystem
$machine = [Guid](Get-ItemProperty -LiteralPath 'HKLM:\SOFTWARE\Microsoft\Cryptography').MachineGuid
$native = [Guid](Get-CimInstance -ClassName Win32_ComputerSystemProduct).UUID
$principal = [Security.Principal.WindowsIdentity]::GetCurrent().Name
$image = Join-Path $PSHOME 'powershell.exe'
if ($os.BuildNumber -ne '20348' -or [int]$os.ProductType -lt 2 -or
    $machine.ToString().ToLowerInvariant() -ne $binding.machine_guid -or
    $native.ToString().ToLowerInvariant() -ne $binding.native_uuid -or
    $principal.ToLowerInvariant() -ne $binding.mapped_user.ToLowerInvariant() -or
    (Get-FileHash -LiteralPath $image -Algorithm SHA256).Hash.ToLowerInvariant() -ne $binding.powershell_sha256) {
    throw 'The original Windows guest, native VM, interpreter or mapped identity differs'
}
$observation = @{build='20348'; machine_guid=$machine.ToString().ToLowerInvariant();
    native_uuid=$native.ToString().ToLowerInvariant(); principal=$principal}
if ($binding.action -ne 'IDENTITY') {
    $service = Get-CimInstance -ClassName Win32_Service -Filter ("Name='" + $binding.service.name + "'")
    if ($null -eq $service -or $service.Name -cne $binding.service.name -or
        $service.PathName -cne $binding.service.image_path -or
        (Get-FileHash -LiteralPath $binding.service.executable -Algorithm SHA256).Hash.ToLowerInvariant() -ne $binding.service.binary_sha256) {
        throw 'The exact originally selected Windows service or executable differs'
    }
    $dependencies = @( (Get-Service -Name $binding.service.name).ServicesDependedOn | Sort-Object -Property Name )
    $expectedDependencies = @( $binding.service.dependencies | Sort-Object )
    if ($dependencies.Count -ne $expectedDependencies.Count) { throw 'Selected service dependency set differs' }
    for ($index = 0; $index -lt $dependencies.Count; $index++) {
        if ($dependencies[$index].Name -cne $expectedDependencies[$index] -or
            ($binding.action -eq 'START_SERVICE' -and $dependencies[$index].Status -ne 'Running')) {
            throw 'A service action would change an unselected dependency'
        }
    }
    switch ($binding.action) {
        'SET_STARTUP' { Set-Service -Name $binding.service.name -StartupType $binding.service.startup }
        'START_SERVICE' { Start-Service -Name $binding.service.name }
        'STOP_SERVICE' { Stop-Service -Name $binding.service.name }
        'OBSERVE_SERVICE' { }
        default { throw 'Unsupported owned Windows action' }
    }
    $current = Get-CimInstance -ClassName Win32_Service -Filter ("Name='" + $binding.service.name + "'")
    $observation.service = @{name=$current.Name; state=$current.State; startup=$current.StartMode;
        image_path=$current.PathName; executable_sha256=(Get-FileHash -LiteralPath $binding.service.executable -Algorithm SHA256).Hash.ToLowerInvariant()}
}
@{format='hosting-windows-guest-observation/1'; action=$binding.action; job_id=$binding.job_id;
    operation_id=$binding.operation_id; selection_sha256=$binding.selection_sha256;
    observation=$observation} | ConvertTo-Json -Compress -Depth 8
'''


@dataclass(frozen=True)
class WindowsGuestSelection:
    canonical: bytes

    def __post_init__(self):
        require(type(self.canonical) is bytes and len(self.canonical) <= 65536,
                'A bounded canonical Windows selection is required')
        value = strict_loads(self.canonical)
        require(type(value) is dict and encoded(value) == self.canonical and value.keys() == {
            'format','guest_profile','native_binding','endpoint','connect_ip','server_name',
            'server_certificate_sha256','ca_sha256','machine_id','machine_guid','native_uuid','mapped_user',
            'certificate_subject','certificate_upn','powershell_sha256','services'}
            and value['format'] == FORMAT and value['guest_profile'] == 'windows-server-2022',
            'One exact Windows Server 2022 native selection is required')
        binding = NativeBinding.from_record(value['native_binding'])
        require(binding.resource_kind == 'vm', 'Windows commands require one observed native VM')
        endpoint = urlsplit(value['endpoint'])
        require(endpoint.scheme == 'https' and endpoint.hostname == value['server_name']
                and not endpoint.username and not endpoint.password and not endpoint.query and not endpoint.fragment
                and endpoint.path == '/wsman' and endpoint.port is not None
                and type(value['server_name']) is str and re.fullmatch('[a-z0-9][a-z0-9.-]{0,252}',value['server_name']),
                'A fixed named HTTPS WinRM listener and port are required')
        address = ipaddress.ip_address(value['connect_ip'])
        require(str(address) == value['connect_ip'] and not address.is_unspecified and not address.is_multicast
                and '%' not in value['connect_ip'], 'An exact commissioned WinRM transport address is required')
        require(all(type(value[key]) is str and _HASH.fullmatch(value[key]) for key in
                ('server_certificate_sha256','ca_sha256','powershell_sha256')),
                'Exact WinRM trust and PowerShell interpreter hashes are required')
        require(type(value['machine_id']) is str and re.fullmatch('[A-Za-z0-9][A-Za-z0-9._:-]{0,127}',value['machine_id'])
                and str(UUID(value['machine_guid'])) == value['machine_guid']
                and str(UUID(value['native_uuid'])) == value['native_uuid']
                and type(value['mapped_user']) is str and re.fullmatch(r'[A-Za-z0-9_.-]{1,63}\\[A-Za-z0-9_.-]{1,63}',value['mapped_user'])
                and type(value['certificate_subject']) is str and 1 <= len(value['certificate_subject']) <= 512
                and not any(char in value['certificate_subject'] for char in '\r\n\x00*')
                and type(value['certificate_upn']) is str
                and re.fullmatch(r'[A-Za-z0-9_.-]{1,63}@[A-Za-z0-9_.-]{1,253}',value['certificate_upn']),
                'The original native UUID, Windows machine and mapped account must be exact')
        if NATIVE_GUEST_PROFILES[binding.platform_family]['dmi_matches_native_id']:
            require(str(UUID(binding.native_id)) == value['native_uuid'],
                    'OpenStack Windows identity must equal the selected native VM UUID')
        services = value['services']
        require(type(services) is list and 1 <= len(services) <= 32,
                'The exact bounded existing Windows service set is required')
        names = set()
        for service in services:
            require(type(service) is dict and service.keys() == {
                'name','image_path','executable','binary_sha256','state','startup','dependencies'}
                and type(service['name']) is str and _SERVICE.fullmatch(service['name'])
                and service['name'].lower() not in names
                and service['state'] in {'Running','Stopped'}
                and service['startup'] in {'Automatic','Manual','Disabled'}
                and not (service['startup']=='Disabled' and service['state']=='Running')
                and type(service['image_path']) is str and 1 <= len(service['image_path']) <= 4096
                and not any(char in service['image_path'] for char in '\r\n\x00')
                and type(service['executable']) is str and PureWindowsPath(service['executable']).is_absolute()
                and PureWindowsPath(service['executable']).drive.lower() == 'c:'
                and '..' not in PureWindowsPath(service['executable']).parts
                and str(PureWindowsPath(service['executable'])) == service['executable']
                and not any(char in service['executable'][2:] for char in '\r\n\x00:*?<>|"'),
                'Windows service commands cannot escape their exact selected name or executable')
            require(type(service['binary_sha256']) is str and _HASH.fullmatch(service['binary_sha256']),
                'Windows service commands cannot escape their exact selected name or executable')
            require(type(service['dependencies']) is list and len(service['dependencies']) <= 16
                    and all(type(name) is str and _SERVICE.fullmatch(name) for name in service['dependencies'])
                    and len({name.lower() for name in service['dependencies']}) == len(service['dependencies'])
                    and service['name'].lower() not in {name.lower() for name in service['dependencies']},
                    'One bounded exact Windows service dependency set required')
            names.add(service['name'].lower())

    @classmethod
    def from_record(cls, record):
        return cls(encoded(record))

    def to_dict(self):
        return strict_loads(self.canonical)

    def require_same_services(self, current):
        """Separate enrolled accounts may read the same immutable guest policy."""
        require(type(current) is WindowsGuestSelection,
                'An exact independently enrolled Windows descriptor is required')
        identities = {'mapped_user', 'certificate_subject', 'certificate_upn'}
        left, right = self.to_dict(), current.to_dict()
        require({key:value for key,value in left.items() if key not in identities} ==
                {key:value for key,value in right.items() if key not in identities},
                'The current Windows owner changed the original VM, listener, image, service or requested policy')

    @property
    def sha256(self):
        return digest(self.canonical)

    def script(self, action, *, job_id, operation_id, service=None):
        require(action in ACTIONS and all(type(value) is str and re.fullmatch(
                '[A-Za-z0-9][A-Za-z0-9._:-]{0,127}',value) for value in (job_id,operation_id)),
                'A fixed original Windows service action is required')
        value = self.to_dict()
        if action == 'IDENTITY':
            require(service is None, 'Identity read cannot carry a service mutation')
        else:
            require(service in value['services'], 'The original selected Windows service is required')
        document = {key:value[key] for key in ('machine_guid','native_uuid','mapped_user','powershell_sha256')}
        document |= {'action':action,'job_id':job_id,'operation_id':operation_id,
                     'selection_sha256':self.sha256,'service':service}
        script = POWERSHELL.replace('__BINDING__',base64.b64encode(encoded(document)).decode('ascii'))
        command = base64.b64encode(script.encode('utf-16-le')).decode('ascii')
        require(len(command) <= 28000, 'Fixed Windows command exceeds its native process argument bound')
        return command
