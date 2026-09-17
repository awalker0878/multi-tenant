#!/usr/bin/env python3
"""Execute a fixed WD14 IPv4 packet fixture in disposable Linux namespaces.

No user interfaces, endpoints, credentials or configuration are accepted. Running
requires explicit --execute. The parent does not configure networking. All links,
addresses, routes, filter tables and socket servers exist under unshare -Urn.
This is NOT a production firewall, hypervisor or HA qualification test.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import selectors
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / 'examples/wd14-routing.json'


def ip4(address: str) -> bool:
    return ipaddress.ip_interface(address).version == 4


def endpoint(data: dict, node: str) -> str:
    return str(ipaddress.ip_interface(next(i['address'] for i in data['nodes'][node]['interfaces']
                                          if ip4(i['address']))).ip)


def validate_fixture(data: dict) -> None:
    """Reject external addresses and changed node/flow scope before mutation."""
    expected = {'NG-D01O','NG-D01R','NG-D02O','NG-D02R','EC-01','EC-02','SE-01','SE-02',
                'processor-01','processor-02','data-01','data-02','resolver','time','logs','repository'}
    if set(data['nodes']) != expected or len(data['approved_flows']) != 10:
        raise ValueError('This runner implements only the fixed WD14 fixture')
    allowed = [ipaddress.ip_network(x) for x in ('192.0.2.0/24','198.51.100.0/24','203.0.113.0/24')]
    for node in data['nodes'].values():
        for item in node['interfaces']:
            addr = ipaddress.ip_interface(item['address'])
            if addr.version == 4 and not any(addr.ip in n for n in allowed):
                raise ValueError('Non-documentation address refused')
        for item in node['routes']:
            network = ipaddress.ip_network(item['destination'])
            if network.version == 4:
                hop = ipaddress.ip_address(item['next_hop'])
                if not any(hop in n for n in allowed):
                    raise ValueError('Non-fixture next hop refused')
                if network.prefixlen != 0 and not any(network.subnet_of(n) for n in allowed):
                    raise ValueError('Non-fixture route refused')
    for flow in data['approved_flows']:
        if flow['protocol'] not in ('tcp', 'udp') or flow['port'] not in (53, 443) or not flow['stateful']:
            raise ValueError('Unimplemented fixture flow')
        if flow['source'] not in expected or flow['destination'] not in expected:
            raise ValueError('Unknown endpoint')


def rules_for(data: dict, node: str, block: tuple[str, str] | None = None) -> str:
    rows = ['# Original disposable IPv4 fixture only; not a production firewall configuration.']
    if block:
        rows.append(f'block any {endpoint(data, block[0])} {endpoint(data, block[1])} 0 - -')
        rows.append(f'block any {endpoint(data, block[1])} {endpoint(data, block[0])} 0 - -')
    for flow in data['approved_flows']:
        if node in flow['via']:
            rows.append(f"allow {flow['protocol']} {endpoint(data, flow['source'])} "
                        f"{endpoint(data, flow['destination'])} {flow['port']} - -")
    return '\n'.join(rows) + '\n'


def execute(args: list[str]) -> str:
    result = subprocess.run(args, capture_output=True, text=True, timeout=8)
    if result.returncode:
        raise RuntimeError(f'{args[0]}: {result.stderr.strip()}')
    return result.stdout


class Worker:
    def __init__(self, name: str):
        self.name = name
        self.process = subprocess.Popen(['unshare', '--net', sys.executable, str(ROOT/'lab/worker.py')],
                                        stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE, text=True, bufsize=1)
        first = self.read()
        if not first.get('ready'):
            raise RuntimeError(f'Namespace worker {name} failed: {first}')
        self.namespace = first['namespace']

    def read(self) -> dict:
        with selectors.DefaultSelector() as selector:
            selector.register(self.process.stdout, selectors.EVENT_READ)
            if not selector.select(8):
                raise TimeoutError(f'Worker timeout: {self.name}')
        line = self.process.stdout.readline()
        if not line:
            raise RuntimeError(f'Worker {self.name} exited: {self.process.stderr.read(1000)}')
        return json.loads(line)

    def call(self, op: str, **args: Any) -> dict:
        assert self.process.stdin
        self.process.stdin.write(json.dumps(dict(op=op, **args)) + '\n')
        self.process.stdin.flush()
        result = self.read()
        if not result.get('ok'):
            raise RuntimeError(f'{self.name}: {result.get("error")}')
        return result['result']

    def close(self) -> None:
        if self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(3)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(3)
        for stream in (self.process.stdin, self.process.stdout, self.process.stderr):
            if stream:
                stream.close()


def host_fingerprint() -> dict:
    values = {}
    for name, args in (('links',['-j','link']), ('routes',['-j','route','show','table','all'])):
        data = json.loads(execute(['ip', *args]))
        # Packet counters and timestamps may change without a configuration change.
        values[name] = data
    values['namespace'] = os.readlink('/proc/self/ns/net')
    return values


def run_inner() -> dict:
    own, original = os.readlink('/proc/self/ns/net'), os.environ.get('HOSTING_LAB_ORIGINAL_NETNS')
    if not original or original == own:
        raise RuntimeError('Fresh network namespace is required')
    links = json.loads(execute(['ip', '-j', 'link']))
    if {x['ifname'] for x in links} != {'lo'}:
        raise RuntimeError('Refusing namespace with existing network links')
    os.environ['HOSTING_LAB_MASTER_NETNS'] = own
    data = json.loads(FIXTURE.read_text())
    validate_fixture(data)
    results: list[dict] = []
    workers: dict[str, Worker] = {}
    start = time.monotonic()

    def record(name: str, passed: bool, observed: Any) -> None:
        results.append({'id': f'PKT-{len(results)+1:03}', 'name': name,
                        'status': 'PASS' if passed else 'FAIL', 'observed': observed})

    def probe(source: str, destination: str, port: int = 443, retained: str | None = None) -> dict:
        return workers[source].call('probe', address=endpoint(data,destination), port=port, retained=retained)

    with tempfile.TemporaryDirectory(prefix='hosting-packet-fixture-') as directory:
        temp = Path(directory)
        helper = temp/'mini_filter'
        execute(['gcc','-std=c11','-Wall','-Wextra','-Werror','-Wno-misleading-indentation','-O2',
                 str(ROOT/'lab/mini_filter.c'),'-o',str(helper)])
        try:
            for name in data['nodes']:
                workers[name] = Worker(name)
            segments: dict[str,list[tuple[str,str]]] = defaultdict(list)
            for name, node in data['nodes'].items():
                for interface in node['interfaces']:
                    if ip4(interface['address']):
                        segments[interface['segment']].append((name,interface['address']))
            interfaces: dict[tuple[str,str],str] = {}
            counter = 0
            for number,(segment,members) in enumerate(segments.items()):
                bridge = f'b{number}'
                execute(['ip','link','add',bridge,'type','bridge'])
                execute(['ip','link','set',bridge,'up'])
                for name,address in members:
                    outer,inner = f'v{counter}a',f'v{counter}b'
                    counter += 1
                    execute(['ip','link','add',outer,'type','veth','peer','name',inner])
                    execute(['ip','link','set',inner,'netns',str(workers[name].process.pid)])
                    execute(['ip','link','set',outer,'master',bridge])
                    execute(['ip','link','set',outer,'up'])
                    workers[name].call('ip',args=['link','set',inner,'up'])
                    workers[name].call('ip',args=['address','add',address,'dev',inner])
                    interfaces[name,segment] = inner
            for name,node in data['nodes'].items():
                workers[name].call('ip',args=['link','set','lo','up'])
                workers[name].call('forward',enabled=node['kind'] in ('native','edge','service_edge'))
                for route in node['routes']:
                    if ipaddress.ip_network(route['destination']).version == 4:
                        workers[name].call('ip',args=['route','add',route['destination'],'via',route['next_hop']])
                (temp/f'{name}.rules').write_text(rules_for(data,name))

            def install(name: str, mode: str, block: tuple[str,str] | None = None) -> dict:
                rules = temp/f'{name}.rules'
                rules.write_text(rules_for(data,name,block))
                return workers[name].call('filter',helper=str(helper),action='install',rules=str(rules),mode=mode)

            def counters(name: str) -> dict:
                return workers[name].call('filter',helper=str(helper),action='dump')

            for name,node in data['nodes'].items():
                mode = 'router' if node['kind'] == 'native' else ('quarantine' if name.startswith(('EC-','SE-')) else 'host')
                install(name,mode)
                if node['kind'] not in ('native','edge','service_edge'):
                    workers[name].call('serve', address=endpoint(data,name), ports=[443,444],dns=name=='resolver')
            time.sleep(0.2)
            # Establish every listener's health locally, independent of the network path.
            healthy = {name: probe(name,name,443) for name in ('processor-01','data-01','processor-02','data-02','resolver','time','logs','repository')}
            record('All challenge servers healthy before negative testing',all(v['success'] for v in healthy.values()),healthy)
            before = counters('EC-01')
            denied = probe('processor-01','data-01')
            after = counters('EC-01')
            record('Initial quarantine blocks an otherwise intended application path',
                   not denied['success'] and after['forward_dropped_packets'] > before['forward_dropped_packets'],
                   {'probe':denied,'before':before,'after':after})
            for name in ('EC-01','EC-02','SE-01','SE-02'):
                install(name,'edge')
            for tenant in ('01','02'):
                record(f'Tenant {tenant} permitted TCP request/reply',
                       (p:=probe(f'processor-{tenant}',f'data-{tenant}'))['success'],p)
            for name in ('processor-01','data-01','processor-02','data-02'):
                for transport in ('udp','tcp','fallback'):
                    p = workers[name].call('dns',address=endpoint(data,'resolver'),transport=transport,large=transport=='fallback')
                    ok = p['success'] and (transport!='fallback' or p.get('transports')==['udp','tcp'])
                    record(f'{name} DNS {transport}',ok,p)
            for source,dest,port,edge in [
                ('processor-01','data-01',444,'EC-01'),('data-01','processor-01',443,'EC-01'),
                ('processor-02','data-02',444,'EC-02'),('processor-01','resolver',443,'EC-01'),
                ('data-01','time',443,'EC-01'),('data-02','logs',443,'EC-02'),
                ('processor-02','repository',443,'EC-02')]:
                health = probe(dest,dest,port)
                before = counters(edge)
                p = probe(source,dest,port)
                after = counters(edge)
                record(f'Edge denies unapproved {source} to {dest}:{port}',
                       health['success'] and not p['success'] and after['forward_dropped_packets']>before['forward_dropped_packets'],
                       {'healthy_control':health,'probe':p,'edge':edge,'before':before,'after':after})
            for source,dest,gateway in [('processor-01','data-02','NG-D01O'),('data-02','processor-01','NG-D02R')]:
                route = workers[gateway].call('ip',args=['-j','route','show','table','main'])['stdout']
                p = probe(source,dest)
                # Both actual route inspection and a live target control are retained.
                target = ipaddress.ip_address(endpoint(data,dest))
                matches = [r for r in json.loads(route) if r.get('dst')!='default' and target in ipaddress.ip_network(r['dst'])]
                record(f'Cross-tenant path absent {source} to {dest}',not matches and not p['success'] and probe(dest,dest)['success'],
                       {'probe':p,'routing_table':json.loads(route),'basis':'NO_ROUTE_NOT_FIREWALL_TIMEOUT'})
            # Delete only the expected service return route; do not invent a permissive fallback.
            workers['resolver'].call('ip',args=['route','del','192.0.2.0/27'])
            p = workers['processor-01'].call('dns',address=endpoint(data,'resolver'),transport='tcp')
            other = workers['processor-02'].call('dns',address=endpoint(data,'resolver'),transport='tcp')
            record('Missing origin-specific DNS return route fails tenant01 but not tenant02',not p['success'] and other['success'],{'affected':p,'unaffected':other})
            workers['resolver'].call('ip',args=['route','add','192.0.2.0/27','via','203.0.113.129'])
            p = workers['processor-01'].call('dns',address=endpoint(data,'resolver'),transport='tcp')
            record('DNS recovers after exact return route restoration',p['success'],p)
            p = probe('processor-01','data-01',retained='existing')
            record('Established fixture session before containment',p['success'],p)
            install('EC-01','edge',('processor-01','data-01'))
            old = probe('processor-01','data-01',retained='existing')
            new = probe('processor-01','data-01')
            unaffected = probe('processor-02','data-02')
            state = counters('EC-01')
            record('Containment blocks existing and new traffic without affecting tenant02',
                   not old['success'] and not new['success'] and unaffected['success'] and state['forward_dropped_packets']>0,
                   {'existing':old,'new':new,'unaffected':unaffected,'edge':state,
                    'semantics':'Traffic stopped; no assertion of TCP reset or connection-table deletion'})
            install('EC-01','edge')
            p = probe('processor-01','data-01')
            record('New session works after authorized fixture containment release',p['success'],p)
            interface = interfaces['EC-01','A01R']
            workers['EC-01'].call('ip',args=['link','set',interface,'down'])
            p,other = probe('processor-01','data-01'),probe('processor-02','data-02')
            record('Tenant01 edge link failure has no substitute permitted path; tenant02 remains available',
                   not p['success'] and other['success'],{'affected':p,'unaffected':other})
            workers['EC-01'].call('ip',args=['link','set',interface,'up'])
            route_observation = json.loads(workers['EC-01'].call('ip',args=['-j','route','show'])['stdout'])
            # Linux may remove static routes when an interface goes down. Link-UP alone
            # is not recovery. Reconcile only the originally approved EC-01 route set.
            for route in data['nodes']['EC-01']['routes']:
                if ipaddress.ip_network(route['destination']).version == 4:
                    workers['EC-01'].call('ip',args=['route','replace',route['destination'],'via',route['next_hop']])
            p = probe('processor-01','data-01')
            record('Link and exact route reconciliation recover permitted traffic',p['success'],
                   {'probe':p,'routes_after_link_up_before_reconcile':route_observation})
            record('Service hosts do not forward packets', all(workers[n].call('forward-status')['all_disabled']
                   for n in ('resolver','time','logs','repository')),
                   {'forwarding':False,'scope':'Fixture service hosts only; not native multi-tenant service authorization'})
            from mtls_scenarios import exercise
            exercise(workers, data, record)
            return {'kind':'LOCAL_NAMESPACE_PACKET_FIXTURE','status':'PASSED_NAMESPACE_FIXTURE' if all(r['status']=='PASS' for r in results) else 'FAILED',
                    'scope':'IPv4 only; fixed documentation addresses; Linux routing/netfilter/socket fixture',
                    'fixture_sha256':hashlib.sha256(FIXTURE.read_bytes()).hexdigest(),
                    'source_sha256':{n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in
                       ('lab/run_namespace_lab.py','lab/worker.py','lab/mini_filter.c','lab/link_config.py','lab/mtls_fixture.py','lab/mtls_scenarios.py')},
                    'native_vendor_qualification':'NOT_RUN','ipv6_packet_execution':'NOT_IMPLEMENTED_IN_THIS_FIXTURE',
                    'production_firewall_selected':False,'namespace_count':len(workers)+1,
                    'kernel':os.uname().release,'elapsed_seconds':round(time.monotonic()-start,3),
                    'checks':results,'passed':sum(r['status']=='PASS' for r in results),
                    'failed':sum(r['status']!='PASS' for r in results),
                    'limitations':['No vendor overlay/hypervisor/API realization','No HA or full ZIP inspection equivalence',
                                   'No NAT/PBR/ECMP/BGP or spoofing qualification','TLS1.3 and fingerprint resource authorization are ephemeral fixture mechanisms, not managed PKI or KMS',
                                   'No enterprise identity federation, CRL/OCSP, encrypted storage or backup integration','No production changes']}
        finally:
            for worker in workers.values():
                worker.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute',action='store_true',help='Run only the fixed isolated namespace fixture')
    parser.add_argument('--output',type=Path,default=ROOT/'build/reports/local_packet_lab.json')
    parser.add_argument('--inner',action='store_true',help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.inner:
        try:
            result = run_inner()
        except Exception as exc:
            result = {'kind':'LOCAL_NAMESPACE_PACKET_FIXTURE','status':'FAILED_OR_BLOCKED_RUNTIME',
                      'error':f'{type(exc).__name__}: {exc}','native_vendor_qualification':'NOT_RUN'}
        print(json.dumps(result))
        return 0 if result['status']=='PASSED_NAMESPACE_FIXTURE' else 2
    if not args.execute:
        parser.error('No changes made. Explicit --execute is required for the disposable fixture.')
    missing = [x for x in ('ip','unshare','gcc') if not shutil.which(x)]
    if sys.platform!='linux' or missing:
        result = {'kind':'LOCAL_NAMESPACE_PACKET_FIXTURE','status':'BLOCKED_RUNTIME','missing':missing}
    else:
        before = host_fingerprint()
        env = dict(os.environ,HOSTING_LAB_ORIGINAL_NETNS=before['namespace'])
        proc = subprocess.Popen(['unshare','--user','--map-root-user','--net',sys.executable,str(Path(__file__).resolve()),'--inner'],
                                env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,start_new_session=True)
        try:
            out,err = proc.communicate(timeout=180)
            result = json.loads(out) if out.strip() else {'status':'BLOCKED_RUNTIME','error':err[-2000:]}
        except (subprocess.TimeoutExpired,json.JSONDecodeError) as exc:
            result = {'status':'FAILED_OR_BLOCKED_RUNTIME','error':type(exc).__name__}
        finally:
            # Reap descendant workers even if a construction error killed the master.
            try:
                os.killpg(proc.pid,signal.SIGTERM)
            except ProcessLookupError:
                pass
            try:
                proc.wait(4)
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid,signal.SIGKILL)
                proc.wait(4)
        after = host_fingerprint()
        result['original_namespace_configuration_unchanged'] = before==after
        if before!=after:
            result['status']='FAILED_HOST_CONFIGURATION_CHANGED'
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='checks'},indent=2))
    return 0 if result.get('status')=='PASSED_NAMESPACE_FIXTURE' else 2


if __name__=='__main__':
    raise SystemExit(main())
