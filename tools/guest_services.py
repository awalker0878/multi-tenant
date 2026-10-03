"""Closed input contract for the Ubuntu workload service profile."""
import base64
import ipaddress
from pathlib import Path
import re
import ssl
import struct

from provisioner.execution.run_files import digest, read_private, require

PROFILE = 'ubuntu-24.04-services-v1'
ASSETS = {'log_ca', 'log_certificate', 'log_key'}


def public_key(value):
    require(isinstance(value, str), 'Ed25519 public key required')
    parts = value.split(' ')
    require(len(parts) == 2 and parts[0] == 'ssh-ed25519', 'Exact Ed25519 public key required')
    raw = base64.b64decode(parts[1], validate=True)
    require(len(raw) == 51 and raw[:19] == struct.pack('>I', 11) + b'ssh-ed25519' + struct.pack('>I', 32),
            'Malformed Ed25519 public key')


def address(value):
    ip = ipaddress.ip_address(value)
    require(ip.version == 4 and str(ip) == value and not (ip.is_loopback or ip.is_unspecified
            or ip.is_multicast or ip.is_link_local), 'Explicit service IPv4 address required')


def validate_services(target, scope):
    services = target['services']
    required = {'ownership_ref', 'resolver_addresses',
        'admin_users', 'user_ca_keys', 'revoked_user_keys', 'breakglass', 'log', 'journal_mib', 'files'}
    require(isinstance(services, dict) and required <= set(services)
            and not set(services) - required - {'backup'}, 'Complete guest service profile required')
    require(re.fullmatch(r'[A-Za-z0-9:._/-]{3,200}', services['ownership_ref']), 'Owned guest-file handoff required')
    for key in ('resolver_addresses', 'admin_users', 'user_ca_keys'):
        require(isinstance(services[key], list) and 1 <= len(services[key]) <= 8
                and len(set(services[key])) == len(services[key]), 'Explicit unique guest service entries required')
    for ip in services['resolver_addresses']:
        address(ip)
    require(target['user'] in services['admin_users'], 'Current certificate account must remain permitted')
    emergency = services['breakglass']
    require(set(emergency) == {'user', 'public_key'} and emergency['user'] not in services['admin_users'],
            'Separate recovery account required')
    for user in services['admin_users'] + [emergency['user']]:
        require(isinstance(user, str) and re.fullmatch(r'[a-z_][a-z0-9_-]{0,31}', user) and user != 'root',
                'Explicit non-root administrator account required')
    require(isinstance(services['revoked_user_keys'], list), 'Explicit revocation list required')
    for key in [*services['user_ca_keys'], *services['revoked_user_keys'], emergency['public_key']]:
        public_key(key)
    require(emergency['public_key'] not in services['revoked_user_keys'], 'Recovery key is revoked')
    log = services['log']
    require(set(log) == {'address', 'peer_name', 'port', 'queue_mib'}, 'Exact TLS collector required')
    address(log['address'])
    require(isinstance(log['peer_name'], str) and len(log['peer_name']) <= 253
            and re.fullmatch(r'[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?', log['peer_name'])
            and '..' not in log['peer_name'] and '.' in log['peer_name'], 'Exact collector certificate name required')
    require(type(log['port']) is int and 1 <= log['port'] <= 65535, 'Collector TCP port required')
    for size in (log['queue_mib'], services['journal_mib']):
        require(type(size) is int and 64 <= size <= 65536, 'Bounded journal/queue capacity required')
    require(set(services['files']) == ASSETS, 'Exact TLS assets required')
    for asset in services['files'].values():
        require(set(asset) == {'path', 'sha256'} and isinstance(asset['path'], str)
                and re.fullmatch(r'/[A-Za-z0-9_./-]+', asset['path'])
                and '..' not in Path(asset['path']).parts
                and re.fullmatch('[0-9a-f]{64}', asset['sha256']), 'Private content-bound TLS asset required')
    if 'backup' in services:
        backup = services['backup']
        require(set(backup) == {'config', 'credentials', 'ca', 'interval_minutes', 'enabled'}, 'Exact backup enrollment required')
        require(type(backup['enabled']) is bool and type(backup['interval_minutes']) is int
                and 15 <= backup['interval_minutes'] <= 1440, 'Explicit backup schedule required')
        from tools.restic_run import validate
        validate(backup['config'], allow_expired=not backup['enabled'])
        require(backup['config']['scope'] == {k: v for k, v in scope.items() if k != 'phase'}
                and backup['config']['member'] == target['hostname']
                and backup['config']['machine_id'] == target['machine_id'], 'Backup enrollment belongs to another guest')
        export_root = Path('/srv/hosting-exports') / scope['tenant_key'] / scope['wsd_key'] / target['hostname']
        source = backup['config']['source']
        require(re.fullmatch(r'/[A-Za-z0-9_./-]+', source) and Path(source).is_relative_to(export_root),
                'Guest backup must stay inside its owned export directory')
        for asset in (backup['credentials'], backup['ca']):
            require(set(asset) == {'path', 'sha256'} and re.fullmatch(r'/[A-Za-z0-9_./-]+', asset['path'])
                    and '..' not in Path(asset['path']).parts and re.fullmatch('[0-9a-f]{64}', asset['sha256']),
                    'Private bound backup credentials/trust required')
    return services


def verify_assets(target, scope):
    services = validate_services(target, scope)
    for asset in services['files'].values():
        require(digest(read_private(asset['path'])) == asset['sha256'], 'Guest service asset changed')
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.load_verify_locations(cafile=services['files']['log_ca']['path'])
    context.load_cert_chain(services['files']['log_certificate']['path'], services['files']['log_key']['path'])
    if 'backup' in services:
        for asset in (services['backup']['credentials'], services['backup']['ca']):
            require(digest(read_private(asset['path'])) == asset['sha256'], 'Backup credential/trust asset changed')


def resolver_bound(output, allowed):
    """Reject unexpected DHCP/per-link DNS alongside the owned global resolver."""
    global_servers = None
    for line in output.splitlines():
        label, separator, values = line.partition(':')
        if not separator:
            continue
        servers = values.split()
        if label.strip() == 'Global':
            global_servers = servers
        for server in servers:
            address(server)
            require(server in allowed, 'Unapproved per-link resolver remains configured')
    require(global_servers is not None and set(global_servers) == set(allowed),
            'Global resolver configuration was not observed')
    return True
