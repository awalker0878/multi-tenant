"""Pure validation used by the local Ansible staging role.

This is a reference-fixture engineering export, not a live IPAM allocation,
security authorization or platform-specific configuration generator.
"""
from __future__ import annotations
import ipaddress
from pathlib import Path
import re

DOCNETS = (ipaddress.ip_network('192.0.2.0/24'),
           ipaddress.ip_network('198.51.100.0/24'),
           ipaddress.ip_network('203.0.113.0/24'))
MARKER = 'HOSTING_STAGING_ONLY\n'


def safe_label(value, field):
    if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]{1,63}', value):
        raise ValueError(f'{field} must be a bounded non-path identifier')
    return value


def validate_bundle(value):
    if not isinstance(value, dict):
        raise ValueError('Engineering bundle must be a mapping')
    fields = {'purpose', 'tenant', 'domain', 'zone_class', 'engineering_record_ref',
              'network_cidr', 'attachment_cidr', 'routes'}
    if set(value) != fields or value.get('purpose') != 'REFERENCE_FIXTURE':
        raise ValueError('Only the explicit reference fixture shape is supported')
    for key in ('tenant','domain','engineering_record_ref'):
        safe_label(value[key], key)
    if value['zone_class'] not in ('PAZ','OZ','RZ'):
        raise ValueError('Unsupported fixture zone')
    def net(text):
        n = ipaddress.ip_network(text, strict=True)
        if n.version != 4 or not any(n.subnet_of(p) for p in DOCNETS):
            raise ValueError('Fixture prefixes must be documentation IPv4 ranges')
        return n
    workload, attach = net(value['network_cidr']), net(value['attachment_cidr'])
    if workload.overlaps(attach) or attach.prefixlen > 30:
        raise ValueError('Separate workload and usable attachment networks required')
    if not isinstance(value['routes'],list) or not 1 <= len(value['routes']) <= 64:
        raise ValueError('One to 64 explicit fixture routes required')
    seen = set()
    for row in value['routes']:
        if not isinstance(row,dict) or set(row) != {'destination','next_hop','owner'}:
            raise ValueError('Exact destination/next-hop/owner route required')
        destination = net(row['destination'])
        hop = ipaddress.ip_address(row['next_hop'])
        if hop not in attach or hop in (attach.network_address, attach.broadcast_address):
            raise ValueError('Next hop must be a usable address on the attachment')
        if str(destination) in seen or destination.overlaps(workload):
            raise ValueError('Duplicate or competing connected route')
        seen.add(str(destination))
        if row['owner'] != value['domain']:
            raise ValueError('Route belongs to a different domain')
    return dict(value, may_apply=False, may_activate=False,
                status='STAGED_REFERENCE_NOT_QUALIFIED')


def staging_directory(root_value, tenant, domain):
    """Require a caller-created, nonsymlink private workspace; never create it here."""
    if not isinstance(root_value,str):
        raise ValueError('Staging root must be a path string')
    root = Path(root_value).expanduser()
    if not root.is_absolute():
        raise ValueError('Absolute staging root required')
    for p in (root, *root.parents):
        if p.is_symlink():
            raise ValueError('Symlink staging path is forbidden')
    resolved = root.resolve()
    if resolved in (Path('/'), Path.home().resolve()) or not root.is_dir():
        raise ValueError('Existing dedicated staging directory required')
    marker = root / '.hosting-staging'
    if marker.is_symlink() or not marker.is_file() or marker.read_text() != MARKER:
        raise ValueError('Explicit staging marker required')
    tenant=safe_label(tenant,'tenant');domain=safe_label(domain,'domain')
    destination=root/f'{tenant}--{domain}'
    if destination.is_symlink() or (destination.exists() and not destination.is_dir()):
        raise ValueError('Unsafe staging destination')
    for name in ('engineering-handoff.json','routes.csv'):
        if (destination/name).is_symlink():
            raise ValueError('Symlink output is forbidden')
    return str(destination)


class FilterModule:
    def filters(self):
        return {'hosting_validate_bundle': validate_bundle,
                'hosting_staging_directory': staging_directory}
