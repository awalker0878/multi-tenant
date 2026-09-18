#!/usr/bin/env python3
"""Run the fixed WD14 IPv6 packet fixture in disposable Linux namespaces.

No target or inventory argument. Explicit --execute required. IPv6 namespace-local
sysctls and nftables must be available; confinement failures remain BLOCKED, never
worked around by remounting /proc or changing the controller's security settings.
"""
from __future__ import annotations
import argparse
from collections import defaultdict
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lab import ipv6_fixture as f
from lab.run_namespace_lab import Worker as PipeWorker


class Worker(PipeWorker):
    def __init__(self, name: str):
        self.name = name
        self.process = subprocess.Popen(['unshare', '--net', sys.executable,
            str(f.ROOT/'lab/ipv6_worker.py'), name], stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1)
        try:
            first = self.read()
            if not first.get('ready'): raise RuntimeError('Worker failed to enter the empty fixture namespace')
            self.namespace = first['namespace']
        except Exception:
            self.close(); raise


def execute(args: list[str]) -> str:
    result = subprocess.run(args, capture_output=True, text=True, timeout=8)
    if result.returncode: raise RuntimeError(f'{args[0]}: {result.stderr.strip()[:1000]}')
    return result.stdout


def fingerprint() -> str:
    # Ignore naturally changing lifetimes/counters, retain actual configuration.
    def stable(value):
        if isinstance(value, dict):
            return {k:stable(v) for k,v in value.items() if k not in
                    ('valid_life_time','preferred_life_time','expires','stats','stats64','cacheinfo','used','lastuse')}
        if isinstance(value, list): return [stable(v) for v in value]
        return value
    data = {'namespace': os.readlink('/proc/self/ns/net')}
    for label, args in [('links',['-j','link']),('addresses',['-j','addr']),
                        ('ipv4_routes',['-4','-j','route','show','table','all']),
                        ('ipv6_routes',['-6','-j','route','show','table','all'])]:
        data[label] = stable(json.loads(execute(['ip',*args])))
    for family in ('ipv4','ipv6'):
        path=Path(f'/proc/sys/net/{family}/conf/all/forwarding')
        data[family+'_forwarding']=path.read_text().strip()
    return hashlib.sha256(json.dumps(data,sort_keys=True).encode()).hexdigest()


def inner() -> dict:
    own=os.readlink('/proc/self/ns/net');original=os.environ.get('HOSTING_LAB_ORIGINAL_NETNS')
    if not original or own==original: raise RuntimeError('Fresh master network namespace required')
    if {name for _,name in socket.if_nameindex()}!={'lo'}: raise RuntimeError('Master namespace must have only loopback')
    os.environ['HOSTING_LAB_MASTER_NETNS']=own
    data=f.load_fixture();workers={};results=[];interface_map={};start=time.monotonic()
    def record(name,passed,observed):
        results.append({'id':f'IP6-{len(results)+1:03}','name':name,'status':'PASS' if passed else 'FAIL','observed':observed})
    def probe(source,destination,**kw):return workers[source].call('probe',address=f.endpoint(data,destination),**kw)
    def counters(node):return workers[node].call('counters')
    def install(node,mode='edge',**kw):return workers[node].call('filter',mode=mode,**kw)
    def dnsprobe(node,transport='tcp',kind='AAAA'):
        return workers[node].call('dns',address=f.endpoint(data,'resolver'),transport=transport,kind=kind)
    try:
        for name in data['nodes']: workers[name]=Worker(name)
        segments=defaultdict(list)
        for name in data['nodes']:
            for iface in f.interfaces(data,name):segments[iface['segment']].append((name,iface['address']))
        count=0
        for index,(segment,members) in enumerate(segments.items()):
            bridge=f'b{index}'
            execute(['ip','link','add',bridge,'type','bridge','mcast_snooping','0'])
            execute(['ip','link','set',bridge,'up'])
            for name,addr in members:
                a,b=f'v{count}a',f'v{count}b';count+=1
                execute(['ip','link','add',a,'type','veth','peer','name',b])
                execute(['ip','link','set',b,'netns',str(workers[name].process.pid)])
                execute(['ip','link','set',a,'master',bridge]);execute(['ip','link','set',a,'up'])
                interface_map[name,segment]=b
        for name,node in data['nodes'].items():
            # Configure only owned worker sysctls; failure is a runtime blocker.
            workers[name].call('configure',enabled=False)
            mode='router' if node['kind']=='native' else 'quarantine' if node['kind'] in ('edge','service_edge') else 'host'
            install(name,mode)
            workers[name].call('ip',args=['link','set','lo','up'])
            for iface in f.interfaces(data,name):
                dev=interface_map[name,iface['segment']]
                workers[name].call('ip',args=['link','set',dev,'up'])
                workers[name].call('ip',args=['-6','addr','add',iface['address'],'dev',dev])
            for route in f.routes(data,name):
                workers[name].call('ip',args=['-6','route','add',route['destination'],'via',route['next_hop']])
            workers[name].call('configure',enabled=node['kind'] in f.ROUTERS)
        # Do not suppress DAD. Wait for actual assigned addresses to leave tentative state.
        ready={};deadline=time.monotonic()+8
        while time.monotonic()<deadline:
            ready={}
            for name in workers:
                rows=json.loads(workers[name].call('ip',args=['-6','-j','addr','show'])['stdout'])
                ready[name]=f.ready_addresses(data,name,rows)
            if all(ready.values()):break
            time.sleep(.2)
        record('Configured IPv6 addresses complete duplicate-address detection',all(ready.values()),ready)
        if not all(ready.values()):raise RuntimeError('Configured IPv6 addresses are missing, tentative or failed DAD')
        hosts=[n for n,node in data['nodes'].items() if node['kind'] not in f.ROUTERS]
        for name in hosts:workers[name].call('serve')
        health={name:probe(name,name) for name in hosts}
        record('All IPv6 challenge listeners healthy before negative tests',all(x['success'] for x in health.values()),health)
        v4={n:json.loads(workers[n].call('ip',args=['-4','-j','addr','show','scope','global'])['stdout']) for n in workers}
        record('No routable IPv4 address exists in IPv6-only workers',all(f.no_global_ipv4(rows) for rows in v4.values()),{'workers_checked':len(v4)})
        before=counters('EC-01');denied=probe('processor-01','data-01');after=counters('EC-01')
        record('Initial quarantine denies the intended IPv6 application path',not denied['success'] and after['forward_drop']>before['forward_drop'],{'probe':denied,'before':before,'after':after})
        for name in ('EC-01','EC-02','SE-01','SE-02'):install(name)
        for tenant in ('01','02'):
            source,target=f'processor-{tenant}',f'data-{tenant}'
            observations={n:counters(n) for n in (f'NG-D{tenant}O',f'EC-{tenant}',f'NG-D{tenant}R')}
            result=probe(source,target);after={n:counters(n) for n in observations}
            record(f'Tenant {tenant} approved IPv6 TCP request/reply crosses its declared chain',result['success'] and all(after[n]['native_forward']>observations[n]['native_forward'] if n.startswith('NG-') else after[n]['new_allow']>observations[n]['new_allow'] for n in observations),{'probe':result,'before':observations,'after':after})
        for name in ('processor-01','data-01','processor-02','data-02'):
            for transport in ('udp','tcp','fallback'):
                result=dnsprobe(name,transport)
                record(f'{name} AAAA lookup over IPv6 {transport}',result['success'] and (transport!='fallback' or result['transports']==['udp','tcp']),result)
        result=dnsprobe('processor-01','tcp','A')
        record('A lookup over IPv6 transport does not establish IPv4 reachability',result['success'],result)
        for source,target,port,edge in [('processor-01','data-01',444,'EC-01'),('data-01','processor-01',443,'EC-01'),
                ('processor-02','data-02',444,'EC-02'),('processor-01','resolver',443,'EC-01'),
                ('data-01','time',443,'EC-01'),('data-02','logs',443,'EC-02'),('processor-02','repository',443,'EC-02')]:
            healthy=probe(target,target,port=port);before=counters(edge);result=probe(source,target,port=port);after=counters(edge)
            record(f'IPv6 policy denies {source} to {target}:{port}',healthy['success'] and not result['success'] and after['forward_drop']>before['forward_drop'],{'healthy_target':healthy,'probe':result,'before':before,'after':after})
        for source,target,router in [('processor-01','data-02','NG-D01O'),('data-02','processor-01','NG-D02R')]:
            table=json.loads(workers[router].call('ip',args=['-6','-j','route','show','table','main'])['stdout'])
            address=ipaddress.ip_address(f.endpoint(data,target))
            matches=[r for r in table if r.get('dst')=='default' or address in ipaddress.ip_network(r['dst'])]
            result=probe(source,target)
            record(f'No routed IPv6 cross-tenant path from {source} to {target}',not matches and not result['success'] and probe(target,target)['success'],{'probe':result,'native_route_table':table,'basis':'NO_MATCHING_ROUTE_WITH_HEALTHY_TARGET'})
        nd={n:counters(n)['nd'] for n in workers}
        neighbors={n:json.loads(workers[n].call('ip',args=['-6','-j','neigh','show'])['stdout']) for n in ('processor-01','NG-D01O','EC-01','NG-D01R','data-01')}
        record('Real neighbour discovery supports the routed application chain',all(nd[n]>0 for n in neighbors) and all(neighbors.values()),{'nd_packets':nd,'neighbor_entries':neighbors})
        # One deliberately unsolicited RA, confined to a fixed private link.
        before=counters('processor-01');old=json.loads(workers['processor-01'].call('ip',args=['-6','-j','route','show','table','main'])['stdout'])
        sent=workers['NG-D01O'].call('advertise-once',interface=interface_map['NG-D01O','D01O']);time.sleep(.1)
        after=counters('processor-01');new=json.loads(workers['processor-01'].call('ip',args=['-6','-j','route','show','table','main'])['stdout'])
        record('Static endpoint rejects unsolicited router advertisement without changing routes',after['control_drop']>before['control_drop'] and old==new,{'sent':sent,'before':before,'after':after,'routes_unchanged':old==new})
        prefix='2001:db8:100:1::/64';workers['resolver'].call('ip',args=['-6','route','del',prefix])
        lost,other=dnsprobe('processor-01'),dnsprobe('processor-02')
        record('Removing tenant01 origin-specific service reply route leaves tenant02 working',not lost['success'] and other['success'],{'affected':lost,'unaffected':other})
        workers['resolver'].call('ip',args=['-6','route','add',prefix,'via','2001:db8:300:1::129'])
        result=dnsprobe('processor-01');record('Exact IPv6 service reply route restoration recovers DNS',result['success'],result)
        result=probe('processor-01','data-01',retained='old');record('Established IPv6 session exists before containment',result['success'],result)
        install('EC-01',contain=True);old=probe('processor-01','data-01',retained='old');new=probe('processor-01','data-01');other=probe('processor-02','data-02');counted=counters('EC-01')
        record('Containment overrides established traffic and new sessions without tenant02 outage',not old['success'] and not new['success'] and other['success'] and counted['containment']>0,{'existing':old,'new':new,'other_tenant':other,'counters':counted})
        install('EC-01');result=probe('processor-01','data-01');record('Explicit fixture containment release restores new IPv6 sessions',result['success'],result)
        dev=interface_map['EC-01','A01R'];workers['EC-01'].call('ip',args=['link','set',dev,'down'])
        result,other=probe('processor-01','data-01'),probe('processor-02','data-02')
        record('Edge-link failure has no alternate permit path and does not affect tenant02',not result['success'] and other['success'],{'affected':result,'unaffected':other})
        lost_addresses=json.loads(workers['EC-01'].call('ip',args=['-6','-j','addr','show','dev',dev])['stdout'])
        workers['EC-01'].call('ip',args=['link','set',dev,'up'])
        restored=next(i['address'] for i in f.interfaces(data,'EC-01') if i['segment']=='A01R')
        workers['EC-01'].call('ip',args=['-6','addr','replace',restored,'dev',dev])
        deadline=time.monotonic()+8
        while True:
            addresses=json.loads(workers['EC-01'].call('ip',args=['-6','-j','addr','show'])['stdout'])
            if f.ready_addresses(data,'EC-01',addresses):break
            if time.monotonic()>=deadline:raise RuntimeError('Exact IPv6 link address failed recovery/DAD')
            time.sleep(.2)
        for route in f.routes(data,'EC-01'):workers['EC-01'].call('ip',args=['-6','route','replace',route['destination'],'via',route['next_hop']])
        result=probe('processor-01','data-01');record('Link, exact IPv6 address and route reconciliation restore service',result['success'],{'probe':result,'before_address_recovery':lost_addresses,'restored_source_address':restored})
        # MTU reduction is only a local packet-path experiment, not VXLAN/overlay qualification.
        workers['EC-01'].call('ip',args=['link','set',dev,'mtu','1280'])
        install('NG-D01O','router',block_ptb=True);before=counters('NG-D01O');large=probe('processor-01','data-01',size=8192);after=counters('NG-D01O');small=probe('processor-01','data-01')
        record('Blocking Packet Too Big disrupts large transfer despite a healthy small exchange',not large['success'] and small['success'] and after['ptb_block']>before['ptb_block'],{'large':large,'small':small,'before':before,'after':after})
        install('NG-D01O','router');before=counters('processor-01');large=probe('processor-01','data-01',size=8192);after=counters('processor-01')
        record('Related Packet Too Big restores transfer and records the 1280-byte path MTU',large['success'] and large.get('path_mtu')==1280 and after['related_error']>before['related_error'],{'large':large,'before':before,'after':after})
        workers['EC-01'].call('ip',args=['link','set',dev,'mtu','1500'])
        forwarding={n:workers[n].call('forward-status') for n in hosts}
        record('Workload and shared-service hosts remain non-forwarding',all(v['forwarding']=='0' for v in forwarding.values()),forwarding)
        # Reuse actual TLS fixture on the IPv6 path, not a second identity implementation.
        from lab.mtls_fixture import material
        with tempfile.TemporaryDirectory(prefix='ipv6-fixture-pki-') as temporary:
            m=material(Path(temporary));workers['data-01'].call('mtls-start',certificate=m['server']['certificate'],key=m['server']['key'],ca=m['ca'],allowed=[m['client']['fingerprint']])
            def tls(label='client',**kwargs):
                cert={} if label is None else {key:m[label][key] for key in ('certificate','key')}
                return workers['processor-01'].call('mtls-probe',address=f.endpoint(data,'data-01'),ca=m['ca'],**cert,**kwargs)
            result=tls();record('TLS1.3 authenticated challenge crosses the actual IPv6 route',result['success'] and result.get('tls_version')=='TLSv1.3',result)
            for label in ('other-tenant','expired','foreign',None):
                denied=tls(label);healthy=tls();record(f'IPv6 service rejects {label or "missing"} client authority with valid positive control',not denied['success'] and healthy['success'],{'rejected':denied,'positive_control':healthy})
            denied=tls(hostname='wrong.fixture.invalid');healthy=tls();record('IPv6 TLS hostname verification remains required',not denied['success'] and healthy['success'],{'rejected':denied,'positive_control':healthy})
            denied=probe('processor-01','data-01');healthy=tls();record('No plaintext fallback on the IPv6 TLS endpoint',not denied['success'] and healthy['success'],{'plaintext':denied,'tls':healthy})
            old=tls(retained='tls-old');state=workers['data-01'].call('mtls-grants',allowed=[m['rotated']['fingerprint']]);denied=tls(retained='tls-old');new=tls('rotated')
            record('IPv6 resource-grant withdrawal closes the old session and permits the new identity',old['success'] and not denied['success'] and new['success'] and state['withdrawn_connections']>0,{'before':old,'old_after':denied,'new':new,'service_state':state})
        record('Temporary IPv6 TLS credential files removed',not Path(temporary).exists(),{'files_exist':Path(temporary).exists()})
        return {'kind':'LOCAL_ROUTED_IPV6_PACKET_FIXTURE','status':'PASSED_IPV6_FIXTURE' if all(r['status']=='PASS' for r in results) else 'FAILED_IPV6_FIXTURE',
            'checks':results,'passed':sum(r['status']=='PASS' for r in results),'failed':sum(r['status']!='PASS' for r in results),
            'fixture_sha256':f.FIXTURE_SHA256,'source_sha256':{p:hashlib.sha256((f.ROOT/p).read_bytes()).hexdigest() for p in
                ('lab/ipv6_fixture.py','lab/ipv6_worker.py','lab/run_ipv6_lab.py','lab/run_namespace_lab.py','lab/mtls_fixture.py')},
            'kernel':os.uname().release,'nft_version':execute(['nft','--version']).strip(),'namespace_count':len(workers)+1,
            'elapsed_seconds':round(time.monotonic()-start,3),'native_vendor_qualification':'NOT_RUN','native_apply':'NOT_RUN',
            'limitations':['Fixed IPv6-only Linux namespace routing; no native vendor, overlay, HA, NAT/PBR/BGP or production firewall qualification',
                'No SLAAC/DHCPv6 offer; static addresses with RA/redirect disabled and one RA rejection observation',
                'No general ND spoofing, fragmentation/extension-header or multicast-snooping qualification',
                'DNS UDP truncation is scripted to test TCP fallback; not a large-DNS-message fragmentation claim',
                'Temporary TLS fingerprint grants are not enterprise PKI, KMS, revocation-service or backup implementation']}
    except Exception as exc:
        return {'kind':'LOCAL_ROUTED_IPV6_PACKET_FIXTURE','status':'FAILED_OR_BLOCKED_RUNTIME','error':f'{type(exc).__name__}: {exc}',
                'checks':results,'passed':sum(r['status']=='PASS' for r in results),'failed':sum(r['status']!='PASS' for r in results),
                'native_vendor_qualification':'NOT_RUN'}
    finally:
        for worker in workers.values():worker.close()


def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute',action='store_true');parser.add_argument('--inner',action='store_true',help=argparse.SUPPRESS)
    parser.add_argument('--output',type=Path,default=f.ROOT/'build/reports/local_ipv6_packet_lab.json');args=parser.parse_args()
    if args.inner:
        result=inner();print(json.dumps(result));return 0 if result['status']=='PASSED_IPV6_FIXTURE' else 2
    if not args.execute:parser.error('No changes made. Explicit --execute is required for the fixed disposable IPv6 lab.')
    f.load_fixture();args.output.parent.mkdir(parents=True,exist_ok=True)
    descriptor=os.open(args.output,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(descriptor,'w') as out:out.write('{"status":"STARTED_INCOMPLETE","native_apply":"NOT_RUN"}\n')
    missing=[name for name in ('ip','unshare','nft') if not shutil.which(name)]
    if sys.platform!='linux' or missing:result={'status':'BLOCKED_RUNTIME','missing':missing,'native_apply':'NOT_RUN'}
    else:
        before=fingerprint();original=os.readlink('/proc/self/ns/net')
        env={key:os.environ[key] for key in ('PATH','LANG','LC_ALL','LD_LIBRARY_PATH') if key in os.environ}
        env.update(HOSTING_LAB_ORIGINAL_NETNS=original,PYTHONDONTWRITEBYTECODE='1')
        proc=subprocess.Popen(['unshare','--user','--map-root-user','--net',sys.executable,str(Path(__file__).resolve()),'--inner'],
            env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,start_new_session=True)
        try:
            out,err=proc.communicate(timeout=240)
            result=json.loads(out) if out.strip() else {'status':'BLOCKED_RUNTIME','error':err[-2000:]}
            if proc.returncode and result.get('status')=='PASSED_IPV6_FIXTURE':result['status']='FAILED_EXIT_STATUS'
        except (subprocess.TimeoutExpired,json.JSONDecodeError) as exc:result={'status':'FAILED_OR_BLOCKED_RUNTIME','error':type(exc).__name__}
        finally:
            try:os.killpg(proc.pid,signal.SIGTERM)
            except ProcessLookupError:pass
            try:proc.wait(4)
            except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL);proc.wait(4)
        after=fingerprint();result.update(original_namespace_configuration_unchanged=before==after,
            original_configuration_sha256_before=before,original_configuration_sha256_after=after)
        if before!=after:result['status']='FAILED_ORIGINAL_CONFIGURATION_CHANGED'
    fd,temp=tempfile.mkstemp(prefix='.ipv6-report-',dir=args.output.parent)
    try:
        with os.fdopen(fd,'w') as out:json.dump(result,out,indent=2);out.write('\n')
        os.replace(temp,args.output)
    finally:Path(temp).unlink(missing_ok=True)
    print(json.dumps({k:v for k,v in result.items() if k!='checks'},indent=2))
    return 0 if result['status']=='PASSED_IPV6_FIXTURE' else 2

if __name__=='__main__':raise SystemExit(main())
