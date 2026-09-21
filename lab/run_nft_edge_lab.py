#!/usr/bin/env python3
"""Real packet test in three owned disposable Linux network namespaces."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
from datetime import timedelta

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.run_files import digest, encoded, utcnow

SERVER = '''import socket,threading
def connection(c):
 with c:
  while True:
   data=c.recv(128)
   if not data: break
   c.sendall(b"hosting-edge-fixture")
def serve(port):
 s=socket.socket();s.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1);s.bind(("10.250.2.2",port));s.listen()
 while True:
  c,_=s.accept();threading.Thread(target=connection,args=(c,),daemon=True).start()
threading.Thread(target=serve,args=(19651,),daemon=True).start()
serve(19652)
'''
PROBE = '''import socket,sys
try:
 with socket.create_connection(("10.250.2.2",int(sys.argv[1])),timeout=.7) as s:
  s.sendall(b"probe"); assert s.recv(128)==b"hosting-edge-fixture"
except (OSError,AssertionError):sys.exit(2)
'''
SESSION = '''import socket,sys
s=socket.create_connection(("10.250.2.2",19652),timeout=1)
s.sendall(b"before");assert s.recv(128)==b"hosting-edge-fixture"
print("READY",flush=True)
sys.stdin.readline()
try:
 s.sendall(b"after");assert s.recv(128)==b"hosting-edge-fixture"
 print("OPEN",flush=True)
except (OSError,AssertionError):print("WITHDRAWN",flush=True)
'''


def run():
    ip, nft = shutil.which('ip'), shutil.which('nft')
    if os.geteuid() != 0 or not ip or not nft:
        raise RuntimeError('Disposable namespace campaign requires root, iproute2 and nftables')
    prefix = 'hfe' + uuid.uuid4().hex[:7]
    names = {k: prefix + '-' + k for k in ('client', 'edge', 'server')}
    created, processes = [], []
    def command(argv):
        return subprocess.check_output(argv, text=True, stderr=subprocess.STDOUT, timeout=20)
    def ns(which, *argv):
        return [ip, 'netns', 'exec', names[which], *argv]
    def probe(port, expected, where='client'):
        result = subprocess.run(ns(where, sys.executable, '-c', PROBE, str(port)), capture_output=True, timeout=4)
        if (result.returncode == 0) != expected:
            raise RuntimeError('Packet result differed from the exact flow policy')
    try:
        for name in names.values():
            command([ip, 'netns', 'add', name]); created.append(name)
        for side, edge_dev, address in [('client', 'domain0', '10.250.1'), ('server', 'service0', '10.250.2')]:
            left, right = prefix + side[0], prefix + side[0] + 'e'
            command([ip, 'link', 'add', left, 'type', 'veth', 'peer', 'name', right])
            command([ip, 'link', 'set', left, 'netns', names[side]])
            command([ip, 'link', 'set', right, 'netns', names['edge']])
            command(ns(side, ip, 'link', 'set', left, 'name', 'eth0'))
            command(ns('edge', ip, 'link', 'set', right, 'name', edge_dev))
            command(ns(side, ip, 'addr', 'add', address + '.2/24', 'dev', 'eth0'))
            command(ns('edge', ip, 'addr', 'add', address + '.1/24', 'dev', edge_dev))
            command(ns(side, ip, 'link', 'set', 'eth0', 'up'))
            command(ns('edge', ip, 'link', 'set', edge_dev, 'up'))
        for side in names:
            command(ns(side, ip, 'link', 'set', 'lo', 'up'))
        command(ns('client', ip, 'route', 'add', '10.250.2.0/24', 'via', '10.250.1.1'))
        command(ns('server', ip, 'route', 'add', '10.250.1.0/24', 'via', '10.250.2.1'))
        command(ns('edge', '/usr/sbin/sysctl', '-w', 'net.ipv4.ip_forward=1'))
        server = subprocess.Popen(ns('server', sys.executable, '-c', SERVER), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        processes.append(server)
        # Healthy endpoints and routing are established before denial testing.
        for _ in range(20):
            if subprocess.run(ns('server', sys.executable, '-c', PROBE, '19651'), capture_output=True).returncode == 0:
                break
            time.sleep(.1)
        probe(19651, True); probe(19652, True)
        with tempfile.TemporaryDirectory(prefix='hosting-edge-packet-lab-') as tmp:
            base = Path(tmp); ledger = base / 'ledger'; ledger.mkdir(mode=0o700)
            spec = dict(format='hosting-nft-edge/1', scope=dict(environment_key='test', site_key='lab-site',
                platform='openstack', tenant_key='tenant-a', wsd_key='science'),
                machine_id=Path('/etc/machine-id').read_text().strip(),
                network_namespace_inode=int(command(ns('edge', 'stat', '-Lc', '%i', '/proc/self/ns/net')).strip()),
                nft_sha256=hashlib.sha256(Path(nft).read_bytes()).hexdigest(), operation_id='local-packet-lab', generation=1,
                interfaces={'domain0': ['10.250.1.0/24'], 'service0': ['10.250.2.0/24']}, owned_interfaces=['domain0'],
                flows=[dict(ingress='domain0', egress='service0', source='10.250.1.2', destination='10.250.2.2',
                            protocol='tcp', port=p, phase=phase) for p, phase in [(19651, 'bootstrap'), (19652, 'active')]],
                max_lease_seconds=5)
            counter = 0
            def apply(mode):
                nonlocal counter
                counter += 1; spec['generation'] = counter
                spec_path = base / f'spec-{counter}.json'; spec_path.write_bytes(encoded(spec)); spec_path.chmod(0o600)
                common = ['--spec', str(spec_path), '--nft', nft, '--execute']
                inspected = json.loads(command(ns('edge', sys.executable, str(ROOT / 'tools/nft_edge.py'), 'inspect',
                                      *common, '--output', str(base / f'inspect-{counter}'))))
                authority = dict(spec_sha256=digest(encoded(spec)), mode=mode, expected_state_sha256=inspected['state_sha256'],
                    valid_from=(utcnow() - timedelta(seconds=1)).isoformat(), valid_until=(utcnow() + timedelta(minutes=5)).isoformat(),
                    change_ref='LOCAL-FIXTURE', boundary_acceptance_ref='LOCAL-FIXTURE', readiness_ref='LOCAL-FIXTURE')
                authority_path = base / f'authority-{counter}.json'
                authority_path.write_bytes(encoded(authority)); authority_path.chmod(0o600)
                try:
                    command(ns('edge', sys.executable, str(ROOT / 'tools/nft_edge.py'), 'apply', *common, '--mode', mode,
                               '--authority', str(authority_path), '--ledger', str(ledger), '--output', str(base / f'apply-{counter}')))
                except subprocess.CalledProcessError as exc:
                    # This campaign owns every synthetic input and has no native
                    # credentials. Retain its engine diagnostic before cleanup.
                    logs = sorted((base / f'apply-{counter}').glob('kernel-*.log'))
                    detail = '\n'.join(p.read_text()[-4000:] for p in logs if p.stat().st_size)
                    raise RuntimeError('Local fixture nft engine: ' + detail) from exc
            apply('withdraw'); probe(19651, False); probe(19652, False)
            apply('bootstrap'); probe(19651, True); probe(19652, False)
            apply('active'); probe(19651, True); probe(19652, True)
            session = subprocess.Popen(ns('client', sys.executable, '-c', SESSION), stdin=subprocess.PIPE,
                                       stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            processes.append(session)
            if session.stdout.readline().strip() != 'READY':
                raise RuntimeError('Established-session positive control failed')
            apply('withdraw')
            session.stdin.write('continue\n'); session.stdin.flush()
            response, _ = session.communicate(timeout=5)
            if response.strip() != 'WITHDRAWN':
                raise RuntimeError('Established connection bypassed withdrawal')
            probe(19652, False); probe(19652, True, 'server')
            apply('active'); probe(19652, True)
            time.sleep(5.2)
            probe(19651, False); probe(19652, False); probe(19652, True, 'server')
            apply('active'); probe(19652, True)
            incident=dict(format='hosting-edge-containment-authority/1',spec_sha256=digest(encoded(spec)),incident_id='local-incident',
                valid_from=(utcnow()-timedelta(seconds=1)).isoformat(),valid_until=(utcnow()+timedelta(minutes=5)).isoformat(),
                change_ref='LOCAL-INCIDENT',boundary_acceptance_ref='LOCAL-BOUNDARY')
            incident_path=base/'incident.json'; incident_path.write_bytes(encoded(incident)); incident_path.chmod(0o600)
            for attempt in ('first','repeat'):
                result=json.loads(command(ns('edge',sys.executable,str(ROOT/'tools/edge_contain.py'),
                    '--spec',str(base/f'spec-{counter}.json'),'--authority',str(incident_path),'--nft',nft,
                    '--ledger',str(ledger),'--output',str(base/('contain-'+attempt)),'--execute')))
                if result['status']!='CONTAINED_OBSERVED_NOT_QUALIFIED' or result['write_attempted']!=(attempt=='first'):
                    raise RuntimeError('Delegated containment did not retain its one native attempt')
                probe(19651,False); probe(19652,False); probe(19652,True,'server')
            return dict(status='PASSED_LOCAL_NATIVE_KERNEL_EDGE_ONLY', healthy_controls=True,
                        bootstrap_scope=True, active_scope=True, established_session_withdrawn=True,
                        controller_loss_expiry=True, delegated_incident_containment=True,
                        containment_retry_read_only=True, native_platform_contacted=False, edge_ha_qualified=False)
    finally:
        for process in processes:
            if process.poll() is None:
                process.terminate()
                try: process.wait(timeout=3)
                except subprocess.TimeoutExpired: process.kill(); process.wait(timeout=3)
        for name in reversed(created):
            subprocess.run([ip, 'netns', 'delete', name], capture_output=True, timeout=10)


def main():
    try:
        report, code = run(), 0
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as exc:
        report, code = dict(status='FAILED_LOCAL_EDGE_CAMPAIGN', reason=str(exc), native_platform_contacted=False), 2
        if isinstance(exc, subprocess.CalledProcessError):
            report['local_fixture_diagnostic'] = exc.output
    path = ROOT / 'build/reports/nft_edge_lab.json'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))
    return code


if __name__ == '__main__':
    raise SystemExit(main())
