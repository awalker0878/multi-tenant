#!/usr/bin/env python3
"""GET-only Nova/Cinder/Glance identity, placement, attachment and image readback."""
import argparse
from datetime import datetime
import http.client
import json
from pathlib import Path
import re
import ssl
import sys
import time
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools import readback_core as c
from tools.run_files import current_window, digest, encoded, load_private, new_directory, read_private, require, utcnow, write_new

KINDS = {
    'server': ('compute', 'servers', 'server', 'compute 2.79', {
        'id', 'tenant_id', 'status', 'OS-EXT-STS:task_state', 'OS-EXT-STS:power_state',
        'OS-EXT-AZ:availability_zone', 'OS-EXT-SRV-ATTR:host', 'OS-EXT-SRV-ATTR:hypervisor_hostname',
        'flavor', 'metadata', 'config_drive', 'os-extended-volumes:volumes_attached'}),
    'volume': ('volume', 'volumes', 'volume', 'volume 3.60', {
        'id', 'os-vol-tenant-attr:tenant_id', 'status', 'size', 'encrypted', 'bootable',
        'availability_zone', 'volume_type', 'attachments', 'metadata'}),
    'image': ('image', 'images', None, None, {
        'id', 'owner', 'status', 'visibility', 'protected', 'disk_format', 'container_format',
        'os_hash_algo', 'os_hash_value', 'min_disk', 'min_ram'}),
}


def validate(manifest):
    c.exact_keys(manifest, {'format', 'scope', 'project_id', 'endpoints', 'resources'})
    require(manifest['format'] == 'hosting-openstack-readback/1', 'Unknown OpenStack observation format')
    c.exact_keys(manifest['scope'], {'environment_key', 'site_key', 'platform', 'tenant_key', 'wsd_key'})
    require(manifest['scope']['platform'] == 'openstack', 'OpenStack scope required')
    for value in manifest['scope'].values(): c.identifier(value)
    require(isinstance(manifest['project_id'], str) and (re.fullmatch(r'[0-9a-f]{32}', manifest['project_id'])
            or c.UUID.fullmatch(manifest['project_id'])), 'Exact project required')
    require(isinstance(manifest['resources'], list) and 1 <= len(manifest['resources']) <= 30, 'Enumerate 1-30 owned native objects')
    needed, seen = set(), set()
    for resource in manifest['resources']:
        c.exact_keys(resource, {'kind', 'id', 'expected'})
        require(resource['kind'] in KINDS and isinstance(resource['id'], str) and c.UUID.fullmatch(resource['id']), 'Exact native UUID required')
        kind = resource['kind']; service, _, _, _, fields = KINDS[kind]
        require((kind, resource['id']) not in seen, 'Duplicate native object')
        seen.add((kind, resource['id'])); needed.add(service)
        c.exact_keys(resource['expected'], fields)
        expected = resource['expected']
        require(expected['id'] == resource['id'], 'Native ID expectation differs')
        c.reject_sensitive(expected)
        if kind in {'server', 'volume'}:
            owner = 'tenant_id' if kind == 'server' else 'os-vol-tenant-attr:tenant_id'
            require(expected[owner] == manifest['project_id'], 'Foreign project expectation')
            require(isinstance(expected['metadata'], dict) and all(expected['metadata'].get(k) == manifest['scope'][k]
                    for k in ('tenant_key',)), 'Scoped native metadata required')
        if kind == 'server':
            require(expected['config_drive'] == 'True', 'Accepted config-drive bootstrap required')
            require(expected['status'] in {'ACTIVE', 'SHUTOFF'} and expected['OS-EXT-STS:task_state'] is None,
                    'Only quiescent stopped/running servers can match')
            require(type(expected['OS-EXT-STS:power_state']) is int and expected['OS-EXT-STS:power_state'] ==
                    (1 if expected['status'] == 'ACTIVE' else 4), 'Consistent Nova power state required')
            for key in ('OS-EXT-AZ:availability_zone', 'OS-EXT-SRV-ATTR:host', 'OS-EXT-SRV-ATTR:hypervisor_hostname'):
                c.text(expected[key])
            require(isinstance(expected['flavor'], dict) and {'vcpus', 'ram', 'disk', 'original_name'} <= expected['flavor'].keys(), 'Concrete compute shape required')
            require(isinstance(expected['os-extended-volumes:volumes_attached'], list)
                    and expected['os-extended-volumes:volumes_attached'], 'Owned retained volume attachments required')
            for attachment in expected['os-extended-volumes:volumes_attached']:
                c.exact_keys(attachment, {'id', 'delete_on_termination'})
                require(c.UUID.fullmatch(attachment['id']) and attachment['delete_on_termination'] is False, 'Retained exact volume required')
        elif kind == 'volume':
            require(expected['encrypted'] is True and type(expected['size']) is int and expected['size'] > 0
                    and expected['status'] in {'available', 'in-use'} and isinstance(expected['attachments'], list),
                    'Encrypted stable volume with explicit attachment set required')
        else:
            require(expected['status'] == 'active' and expected['protected'] is True
                    and expected['os_hash_algo'] in {'sha256', 'sha512'}, 'Protected image with strong content hash required')
            require(re.fullmatch('[0-9a-f]{' + ('64' if expected['os_hash_algo'] == 'sha256' else '128') + '}', expected['os_hash_value']), 'Exact image hash required')
    c.exact_keys(manifest['endpoints'], needed)
    for service, endpoint in manifest['endpoints'].items():
        p = urlsplit(endpoint)
        c.origin('https://' + p.netloc)
        require(p.scheme == 'https' and not p.query and not p.fragment and not p.username and not p.password
                and p.path and re.fullmatch(r'/[A-Za-z0-9_./-]+', p.path) and '..' not in p.path
                and not endpoint.endswith('/'), 'Exact catalog endpoint without redirect/discovery required')
        if service == 'compute': require(p.path.endswith('/v2.1') or p.path.endswith('/v2.1/' + manifest['project_id']), 'Compute v2.1 endpoint required')
        elif service == 'volume': require(p.path.endswith('/v3/' + manifest['project_id']), 'Project-bound Cinder v3 endpoint required')
        else: require(p.path.endswith('/v2'), 'Glance v2 endpoint required')


class Client:
    def __init__(self, manifest, token, ca, authority):
        validate(manifest); c.text(token, 'injected token', 8192)
        self.manifest, self.token, self.authority = manifest, token, authority
        self.deadline = time.monotonic() + 120
        self.context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        self.context.minimum_version = ssl.TLSVersion.TLSv1_2
        self.context.verify_flags |= ssl.VERIFY_X509_STRICT
        self.context.load_verify_locations(cadata=ca.decode('ascii'))

    def get(self, resource):
        require(resource in self.manifest['resources'], 'Unaccepted object selector')
        current_window(self.authority)
        service, collection, envelope, version, fields = KINDS[resource['kind']]
        endpoint = urlsplit(self.manifest['endpoints'][service])
        remaining = min(self.deadline - time.monotonic(),
            (datetime.fromisoformat(self.authority['valid_until'].replace('Z', '+00:00')) - utcnow()).total_seconds())
        require(remaining > 0, 'Native read budget exhausted')
        connection = http.client.HTTPSConnection(endpoint.hostname, endpoint.port or 443,
            context=self.context, timeout=min(5, remaining))
        headers = {'X-Auth-Token': self.token, 'Accept': 'application/json', 'Accept-Encoding': 'identity', 'Connection': 'close'}
        if version: headers['OpenStack-API-Version'] = version
        try:
            connection.request('GET', endpoint.path + '/' + collection + '/' + resource['id'], headers=headers)
            sock = connection.sock
            response = connection.getresponse()
            require(response.status == 200 and response.getheader('Content-Type', '').split(';')[0] == 'application/json'
                    and response.getheader('Content-Encoding', 'identity') == 'identity', 'Native response rejected')
            if version: require(response.getheader('OpenStack-API-Version') == version, 'Native microversion differs')
            sizes = response.headers.get_all('Content-Length', [])
            require(len(sizes) <= 1 and (not sizes or sizes[0].isdigit() and int(sizes[0]) <= c.LIMIT)
                    and not (sizes and response.getheader('Transfer-Encoding')), 'Ambiguous native response framing')
            data = bytearray()
            while True:
                current_window(self.authority)
                remaining = min(self.deadline - time.monotonic(),
                    (datetime.fromisoformat(self.authority['valid_until'].replace('Z', '+00:00')) - utcnow()).total_seconds())
                require(remaining > 0, 'Native read budget exhausted')
                if sock and sock.fileno() >= 0: sock.settimeout(min(5, remaining))
                part = response.read1(min(65536, c.LIMIT + 1 - len(data)))
                if not part: break
                data.extend(part); require(len(data) <= c.LIMIT, 'Native response too large')
            require(not sizes or len(data) == int(sizes[0]), 'Truncated native response')
            document = c.strict_loads(data)
            actual = document[envelope] if envelope else document
            require(isinstance(actual, dict), 'Native object missing')
            return {key: actual[key] for key in fields if key in actual}
        finally:
            connection.close()


def observe(manifest, client):
    validate(manifest); captures = []
    for resource in manifest['resources']:
        try:
            before, after = client.get(resource), client.get(resource)
            differences = c.differences(after, resource['expected'])
            stable = c.digest(before) == c.digest(after)
            captures.append({'kind': resource['kind'], 'id': resource['id'], 'status': 'MATCH' if stable and not differences else 'HOLD',
                             'stable': stable, 'differences': differences, 'sha256': c.digest(after)})
        except (OSError, ValueError, KeyError, TypeError, http.client.HTTPException):
            captures.append({'kind': resource['kind'], 'id': resource['id'], 'status': 'INCONCLUSIVE'})
    return {'format': 'hosting-openstack-observation/1', 'scope': manifest['scope'], 'project_id': manifest['project_id'],
            'status': 'OBSERVED_MATCH_NOT_QUALIFIED' if all(x['status'] == 'MATCH' for x in captures) else 'HOLD',
            'manifest_sha256': c.digest(manifest), 'completed_at': utcnow().isoformat(), 'captures': captures,
            'mutations_performed': False, 'production_qualified': False}


def main():
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('manifest', type=Path)
    for name in ('token', 'ca', 'authority', 'output'): p.add_argument('--' + name, type=Path)
    p.add_argument('--execute', action='store_true'); args = p.parse_args()
    try:
        raw = read_private(args.manifest); manifest = c.strict_loads(raw); validate(manifest)
        if not args.execute: print('{"status":"VALIDATED_NO_CONTACT"}'); return 0
        require(all((args.token, args.ca, args.authority, args.output)), 'Private target authority required')
        token, ca = read_private(args.token), read_private(args.ca); authority = load_private(args.authority)
        c.exact_keys(authority, {'manifest_sha256', 'token_sha256', 'ca_sha256', 'valid_from', 'valid_until', 'change_ref'})
        require(all(authority[k + '_sha256'] == digest(v) for k, v in [('manifest', raw), ('token', token), ('ca', ca)]), 'Native authority differs')
        c.text(authority['change_ref']); current_window(authority)
        output = new_directory(args.output, ROOT)
        write_new(output / 'started.json', encoded({'status': 'HOLD_INCOMPLETE', 'manifest_sha256': digest(raw)}))
        result = observe(manifest, Client(manifest, token.decode().strip(), ca, authority))
        write_new(output / 'observation.json', encoded(result)); print(json.dumps({'status': result['status']}))
        return 0 if result['status'] == 'OBSERVED_MATCH_NOT_QUALIFIED' else 2
    except (OSError, ValueError, KeyError, TypeError):
        print('{"status":"HOLD_INPUT_OR_TRANSPORT"}'); return 2


if __name__ == '__main__': raise SystemExit(main())
