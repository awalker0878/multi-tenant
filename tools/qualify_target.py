#!/usr/bin/env python3
"""Collect real native readback and controlled guest traffic evidence, not acceptance."""
import argparse
from datetime import datetime
import ipaddress
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools import readback_core as c, neutron_observe, nsx_observe, nutanix_observe
from tools.check_release import verify
from tools.guest_inventory import build
from tools.run_files import (current_window, digest, encoded, load_private, new_directory,
    read_private, replace_private, require, utcnow, write_new)

ASSETS = {'inventory', 'native_manifest', 'native_credentials', 'native_ca',
          'ssh_key', 'ssh_certificate', 'probe_ca'}
ADAPTERS = {'openstack': neutron_observe, 'vmware': nsx_observe, 'nutanix': nutanix_observe}


def validate(plan):
    c.exact_keys(plan, {'format', 'scope', 'source_commit', 'origin', 'assets', 'cases'})
    require(plan['format'] == 'hosting-target-campaign/1', 'Unknown target campaign')
    c.exact_keys(plan['scope'], {'environment_key', 'site_key', 'platform', 'tenant_key', 'wsd_key'})
    for value in plan['scope'].values():
        c.identifier(value)
    require(plan['scope']['platform'] in ADAPTERS and re.fullmatch('[0-9a-f]{40}', plan['source_commit']),
            'Exact platform and committed source required')
    require(c.origin(plan['origin']) == plan['origin'], 'Canonical native HTTPS origin required')
    c.exact_keys(plan['assets'], ASSETS)
    for asset in plan['assets'].values():
        c.exact_keys(asset, {'path', 'sha256'})
        require(isinstance(asset['path'], str) and Path(asset['path']).is_absolute()
                and re.fullmatch('[0-9a-f]{64}', asset['sha256']), 'Exact private campaign asset required')
    require(isinstance(plan['cases'], list) and 1 <= len(plan['cases']) <= 32, 'Enumerate 1-32 exact traffic cases')
    cases = {}
    for case in plan['cases']:
        c.exact_keys(case, {'id', 'guest', 'destination', 'port', 'server_name', 'path',
                            'body_sha256', 'expect', 'healthy_control'})
        c.identifier(case['id']); c.identifier(case['guest'])
        require(case['id'] not in cases, 'Duplicate traffic case')
        cases[case['id']] = case
        address = ipaddress.ip_address(case['destination'])
        require(address.version == 4 and str(address) == case['destination'] and not
                (address.is_loopback or address.is_link_local or address.is_multicast or address.is_unspecified),
                'Exact workload IPv4 endpoint required')
        require(type(case['port']) is int and 1 <= case['port'] <= 65535, 'Exact destination port required')
        require(isinstance(case['server_name'], str) and len(case['server_name']) <= 253
                and re.fullmatch(r'[a-z0-9][a-z0-9.-]*[a-z0-9]', case['server_name'])
                and '..' not in case['server_name'], 'Exact TLS peer name required')
        require(isinstance(case['path'], str) and re.fullmatch(r'/[A-Za-z0-9_./-]*', case['path'])
                and len(case['path']) <= 256 and '..' not in case['path'], 'Fixed read-only health path required')
        require(re.fullmatch('[0-9a-f]{64}', case['body_sha256']) and case['expect'] in {'allow', 'deny'},
                'Exact expected health bytes and result required')
    for case in cases.values():
        if case['expect'] == 'allow':
            require(case['healthy_control'] is None, 'Positive cases do not reference controls')
        else:
            control = cases.get(case['healthy_control'])
            require(control is not None and control['expect'] == 'allow' and control['guest'] != case['guest']
                    and all(control[k] == case[k] for k in ('destination', 'port', 'server_name', 'path', 'body_sha256')),
                    'Every denial requires a distinct healthy source to the same exact service')
    return cases


def bound_inputs(plan, known_hosts):
    validate(plan)
    assets = {}
    for key, asset in plan['assets'].items():
        raw = read_private(asset['path'])
        require(len(raw) <= 4 * 1024 * 1024 and digest(raw) == asset['sha256'], 'Campaign asset changed or oversized')
        assets[key] = raw
    inventory = c.strict_loads(assets['inventory'])
    variables = inventory['all']['vars']
    access = variables['hosting_guest_access']
    require(access['scope'] == plan['scope'] | {'phase': 'workloads'}, 'Foreign guest scope')
    _, pins = build(variables['hosting_workload_outputs'], access, known_hosts)
    # Inventory connection overrides never enter the transport. Only the freshly
    # rebuilt exact targets and public host keys are used.
    require(all(case['guest'] in access['targets'] for case in plan['cases']), 'Unknown guest selector')
    require(all(ipaddress.ip_address(t['address']).version == 4 for t in access['targets'].values()), 'IPv4 campaign required')
    manifest = c.strict_loads(assets['native_manifest'])
    adapter = ADAPTERS[plan['scope']['platform']]
    if adapter is neutron_observe:
        adapter.validate_manifest(manifest)
    else:
        adapter.validate(manifest)
        require(manifest['origin'] == plan['origin'] and manifest['contact_enabled'] is True, 'Native manifest contact differs')
    return assets, access, pins


def authority_matches(authority, plan_bytes, source, ssh_bytes):
    c.exact_keys(authority, {'format', 'plan_sha256', 'source_commit', 'ssh_sha256',
                            'valid_from', 'valid_until', 'change_ref', 'target_binding_ref', 'isolation_ref'})
    require(authority['format'] == 'hosting-target-campaign-authority/1'
            and authority['plan_sha256'] == digest(plan_bytes) and authority['source_commit'] == source
            and authority['ssh_sha256'] == digest(ssh_bytes), 'Campaign authority differs')
    for key in ('change_ref', 'target_binding_ref', 'isolation_ref'):
        c.text(authority[key])
    current_window(authority)


def budget(authority, maximum):
    current_window(authority)
    remaining = (datetime.fromisoformat(authority['valid_until'].replace('Z', '+00:00')) - utcnow()).total_seconds()
    require(remaining >= maximum + 2, 'Insufficient authority for the next bounded observation')
    return maximum


def native_readback(plan, assets, authority, directory, label):
    platform = plan['scope']['platform']
    script = {'openstack': 'neutron_observe.py', 'vmware': 'nsx_observe.py', 'nutanix': 'nutanix_observe.py'}[platform]
    output = directory / (label + '.json')
    argv = [sys.executable, str(ROOT / 'tools' / script), str(directory / 'native_manifest'),
            '--read-authorized-target', '--expected-origin', plan['origin'],
            '--ca-file', str(directory / 'native_ca'), '--output', str(output)]
    credentials = c.strict_loads(assets['native_credentials'])
    env = {'PATH': '/usr/bin:/bin', 'LANG': 'C.UTF-8', 'PYTHONDONTWRITEBYTECODE': '1'}
    if platform == 'openstack':
        c.exact_keys(credentials, {'token'})
        c.text(credentials['token'], length=8192)
        env['OS_TOKEN'] = credentials['token']
        argv += ['--endpoint', plan['origin'] + '/v2.0']
    else:
        c.exact_keys(credentials, {'username', 'password'})
        for key in credentials:
            c.text(credentials[key], length=4096)
            env[('NSXT' if platform == 'vmware' else 'NUTANIX') + '_' + key.upper()] = credentials[key]
    with os.fdopen(os.open(directory / (label + '.log'), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600), 'wb') as log:
        result = subprocess.run(argv, stdin=subprocess.DEVNULL, stdout=log, stderr=log,
                                env=env, timeout=budget(authority, 120), umask=0o077)
    require(result.returncode == 0, 'Native readback failed; exposure must remain held')
    report = load_private(output)
    require(report.get('outcome', report.get('status')) in {'READBACK_MATCH_NOT_QUALIFIED', 'OBSERVED_MATCH_NOT_QUALIFIED'},
            'Native readback is not stable and matching')
    return digest(read_private(output))


def ssh_probe(case, target, authority, directory, binary, ca, sequence):
    require(utcnow() < datetime.fromisoformat(target['access_valid_until'].replace('Z', '+00:00')), 'Guest access expired')
    payload = case | {'machine_id': target['machine_id'], 'source': target['address'], 'ca_pem': ca.decode('ascii')}
    fixed = (ROOT / 'tools/guest_probe.py').read_text()
    argv = [str(binary), '-F', '/dev/null', '-T', '-i', str(directory / 'ssh_key'),
            '-p', str(target['port']), '-l', target['user']]
    settings = ['BatchMode=yes', 'StrictHostKeyChecking=yes', 'UpdateHostKeys=no',
        'GlobalKnownHostsFile=/dev/null', 'UserKnownHostsFile=' + str(directory / 'known_hosts'),
        'CertificateFile=' + str(directory / 'ssh_certificate'), 'IdentitiesOnly=yes', 'IdentityAgent=none',
        'PubkeyAcceptedAlgorithms=ssh-ed25519-cert-v01@openssh.com', 'ForwardAgent=no', 'ClearAllForwardings=yes',
        'ProxyCommand=none', 'ProxyJump=none', 'ConnectionAttempts=1', 'ConnectTimeout=5',
        'ServerAliveInterval=3', 'ServerAliveCountMax=1', 'LogLevel=ERROR']
    for option in settings:
        argv += ['-o', option]
    argv += [target['address'], '/usr/bin/python3 -I -c ' + shlex.quote(fixed)]
    output = directory / f'ssh-{sequence}.json'
    with os.fdopen(os.open(directory / f'ssh-{sequence}.log', os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600), 'wb') as log, \
         os.fdopen(os.open(output, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600), 'wb') as out:
        result = subprocess.run(argv, input=encoded(payload), stdout=out, stderr=log,
            env={'PATH': '/usr/bin:/bin', 'LANG': 'C.UTF-8'}, timeout=budget(authority, 20), umask=0o077)
    if result.returncode != 0 or output.stat().st_size > 4096:
        return {'status': 'SSH_INCONCLUSIVE'}
    value = c.strict_loads(output.read_bytes())
    c.exact_keys(value, {'status'})
    require(value['status'] in {'WRONG_GUEST', 'BLOCKED', 'INCONCLUSIVE', 'UNEXPECTED_CONNECTION',
                              'HEALTHY', 'UNHEALTHY'}, 'Unexpected guest observation')
    return value


def traffic_campaign(cases, observe):
    observations = []
    for case in cases.values():
        if case['expect'] == 'deny':
            control = cases[case['healthy_control']]
            before = observe(control)
            denied = observe(case) if before['status'] == 'HEALTHY' else {'status': 'NOT_ATTEMPTED'}
            after = observe(control)
            passed = before['status'] == after['status'] == 'HEALTHY' and denied['status'] == 'BLOCKED'
            evidence = {'before': before, 'traffic': denied, 'after': after}
        else:
            observed = observe(case)
            passed, evidence = observed['status'] == 'HEALTHY', {'traffic': observed}
        observations.append({'id': case['id'], 'passed': passed, **evidence})
        if not passed:
            break
    return observations


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('plan', type=Path)
    parser.add_argument('--authority', type=Path)
    parser.add_argument('--ssh', type=Path, default=Path('/usr/bin/ssh'))
    parser.add_argument('--output', type=Path)
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    directory = None
    try:
        raw = read_private(args.plan); plan = c.strict_loads(raw); cases = validate(plan)
        if not args.execute:
            print('{"status":"VALIDATED_NO_CONTACT"}'); return 0
        require(args.authority and args.output, 'Current private authority and new output required')
        source = verify(ROOT)
        require(source['status'] == 'HASHES_MATCH' and source['commit'] == plan['source_commit'], 'Clean exact source required')
        binary = args.ssh.resolve(strict=True)
        authority = load_private(args.authority)
        authority_matches(authority, raw, source['commit'], binary.read_bytes())
        require('.invalid' not in plan['origin'], 'Documentation endpoint refused')
        assets, access, pins = bound_inputs(plan, str(args.output.absolute() / 'known_hosts'))
        directory = new_directory(args.output, ROOT)
        write_new(directory / 'plan.json', raw)
        write_new(directory / 'authority.json', encoded(authority))
        # Copy only assets the child processes need; API credentials stay in memory.
        for key in ('native_manifest', 'native_ca', 'ssh_key', 'ssh_certificate'):
            write_new(directory / key, assets[key])
        write_new(directory / 'known_hosts', pins.encode())
        result = {'status': 'HOLD_INCOMPLETE', 'scope': plan['scope'], 'source_commit': source['commit'],
                  'plan_sha256': digest(raw), 'started_at': utcnow().isoformat(), 'production_qualified': False}
        write_new(directory / 'result.json', encoded(result))
        before = native_readback(plan, assets, authority, directory, 'native-before')
        sequence = 0
        def observe(case):
            nonlocal sequence
            sequence += 1
            target = access['targets'][case['guest']] | {'access_valid_until': access['valid_until']}
            answer = ssh_probe(case, target, authority, directory, binary, assets['probe_ca'], sequence)
            write_new(directory / f'probe-{sequence}.json', encoded({'case': case['id'], **answer, 'observed_at': utcnow().isoformat()}))
            return answer
        observations = traffic_campaign(cases, observe)
        after = native_readback(plan, assets, authority, directory, 'native-after')
        passed = len(observations) == len(cases) and all(o['passed'] for o in observations)
        result |= {'status': 'COLLECTED_REQUIRES_INDEPENDENT_ACCEPTANCE' if passed else 'HOLD_FAILED_TRAFFIC',
                   'native_before_sha256': before, 'native_after_sha256': after, 'cases': observations,
                   'completed_at': utcnow().isoformat()}
        replace_private(directory / 'result.json', encoded(result))
        print(json.dumps({'status': result['status'], 'production_qualified': False}))
        return 0 if passed else 2
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError):
        print('{"status":"HOLD_INCOMPLETE","production_qualified":false}')
        return 2
    finally:
        if directory:
            # Preserve evidence and public trust; remove the extra private key copy.
            (directory / 'ssh_key').unlink(missing_ok=True)


if __name__ == '__main__':
    raise SystemExit(main())
