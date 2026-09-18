"""Offline regression of IPv6 lab boundaries; not a routed packet qualification."""
from __future__ import annotations
from copy import deepcopy
import ipaddress
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import dns.flags
import dns.message
import dns.rrset
from lab import ipv6_fixture as f, ipv6_worker as worker, run_ipv6_lab as routed


class FixedScopeTests(unittest.TestCase):
    def setUp(self):self.data=f.load_fixture()
    def test_exact_unchanged_source(self):self.assertEqual(len(self.data['nodes']),16)
    def test_bad_fixture_digest_stops(self):
        with patch.object(Path,'read_bytes',return_value=b'{}'),self.assertRaises(ValueError):f.load_fixture()
    def test_all_addresses_are_documentation_ipv6(self):
        for name in self.data['nodes']:
            for row in f.interfaces(self.data,name):self.assertIn(ipaddress.ip_interface(row['address']).ip,f.DOCUMENTATION)
    def test_actual_and_non_v6_addresses_rejected(self):
        for value in ('::1','fe80::1','::','192.0.2.1','2606:4700::1111','2001:db9::1'):
            with self.subTest(value=value),self.assertRaises(ValueError):f.address(value)
    def test_exact_v6_routes_only(self):
        for name in self.data['nodes']:
            self.assertTrue(all(ipaddress.ip_network(r['destination']).version==6 for r in f.routes(self.data,name)))
    def test_no_router_default(self):
        for name,node in self.data['nodes'].items():
            if node['kind'] in f.ROUTERS:self.assertNotIn('::/0',[r['destination'] for r in f.routes(self.data,name)])
    def test_service_reply_routes_not_default(self):
        self.assertEqual(len(f.routes(self.data,'resolver')),4)
    def test_namespace_requires_both_parent_identities(self):
        with patch.dict(os.environ,{},clear=True),self.assertRaises(RuntimeError):f.namespace_guard()
    def test_original_namespace_refused(self):
        with patch.dict(os.environ,{'HOSTING_LAB_ORIGINAL_NETNS':'net:[own]','HOSTING_LAB_MASTER_NETNS':'net:[master]'}),patch.object(os,'readlink',return_value='net:[own]'),self.assertRaises(RuntimeError):f.namespace_guard()
    def test_master_namespace_refused(self):
        with patch.dict(os.environ,{'HOSTING_LAB_ORIGINAL_NETNS':'net:[original]','HOSTING_LAB_MASTER_NETNS':'net:[own]'}),patch.object(os,'readlink',return_value='net:[own]'),self.assertRaises(RuntimeError):f.namespace_guard()
    def test_interface_scope(self):
        self.assertEqual(f.safe_interface('v123b'),'v123b')
        for value in ('eth0','all','lo','v1b/forwarding','../all','v1000b'):
            with self.subTest(value=value),self.assertRaises(ValueError):f.safe_interface(value)


class HostFingerprintTests(unittest.TestCase):
    def base(self):
        return {
            'namespace':'net:[100]',
            'links':[
                {'ifindex':2,'ifname':'eth0','mtu':1500,'flags':['BROADCAST','UP','LOWER_UP'],
                 'stats64':{'rx':1}},
                {'ifindex':1,'ifname':'lo','mtu':65536,'flags':['LOOPBACK','UP']}],
            'addresses':[{'ifindex':2,'addr_info':[
                {'family':'inet6','local':'2001:db8::10','prefixlen':64,
                 'valid_life_time':100,'preferred_life_time':50}]}],
            'ipv4_routes':[{'dst':'default','gateway':'192.0.2.1','dev':'eth0','metric':100}],
            'ipv6_routes':[{'dst':'2001:db8::/64','dev':'eth0','metric':100,'expires':30}],
            'ipv4_forwarding':'0','ipv6_forwarding':'0'}

    def test_equivalent_order_and_volatile_fields_have_same_digest(self):
        one=self.base();two=deepcopy(one)
        two['links'].reverse();two['links'][0]['flags'].reverse()
        two['addresses'][0]['addr_info'][0]['valid_life_time']=1
        two['addresses'][0]['addr_info'][0]['preferred_life_time']=1
        two['ipv6_routes'][0]['expires']=1
        self.assertEqual(routed.fingerprint(one),routed.fingerprint(two))

    def test_mtu_change_is_detected(self):
        one=self.base();two=deepcopy(one);two['links'][0]['mtu']=1400
        self.assertNotEqual(routed.fingerprint(one),routed.fingerprint(two))

    def test_address_change_is_detected(self):
        one=self.base();two=deepcopy(one);two['addresses'][0]['addr_info'][0]['local']='2001:db8::11'
        self.assertNotEqual(routed.fingerprint(one),routed.fingerprint(two))

    def test_route_change_is_detected(self):
        one=self.base();two=deepcopy(one);two['ipv4_routes'][0]['gateway']='192.0.2.254'
        self.assertNotEqual(routed.fingerprint(one),routed.fingerprint(two))

    def test_forwarding_change_is_detected(self):
        one=self.base();two=deepcopy(one);two['ipv6_forwarding']='1'
        self.assertNotEqual(routed.fingerprint(one),routed.fingerprint(two))

    def test_section_fingerprints_identify_changed_area_without_raw_values(self):
        one=self.base();two=deepcopy(one);two['links'][0]['mtu']=1400
        before=routed.section_fingerprints(one);after=routed.section_fingerprints(two)
        self.assertNotEqual(before['links'],after['links'])
        for key in set(before)-{'links'}:self.assertEqual(before[key],after[key])


class PolicyTests(unittest.TestCase):
    def setUp(self):self.data=f.load_fixture()
    def test_quarantine_has_no_forward_allow(self):
        rules=f.policy(self.data,'EC-01','quarantine').split(' chain forward ')[1].split(' chain output ')[0]
        self.assertNotIn('accept',rules);self.assertIn('policy drop',rules)
    def test_containment_precedes_established(self):
        rules=f.policy(self.data,'EC-01','edge',contain=True).split(' chain forward ')[1]
        self.assertLess(rules.index('counter name containment drop'),rules.index('ct state established'))
    def test_no_rules_for_unspecified_time_or_log_ports(self):
        rules=f.policy(self.data,'EC-01','edge')
        self.assertNotIn('dport 123',rules);self.assertNotIn('dport 514',rules)
    def test_edge_does_not_allow_echo_or_blanket_icmp(self):
        rules=f.policy(self.data,'EC-01','edge')
        self.assertNotIn('echo-request',rules);self.assertIn('icmpv6 type { 1, 2, 3, 4 } ct state related',rules)
    def test_neighbor_checks_need_hop_limit(self):self.assertIn('ip6 hoplimit 255 icmpv6 type { 135, 136 }',f.policy(self.data,'EC-01','edge'))
    def test_no_flush_global_ruleset(self):
        rules=f.policy(self.data,'EC-01','edge',replace=True)
        self.assertNotIn('flush ruleset',rules);self.assertTrue(rules.startswith('delete table ip6 hosting_v6_fixture'))
    def test_no_implicit_truthy_policy_switch(self):
        for key in ('replace','contain','block_ptb'):
            with self.subTest(key=key),self.assertRaises(ValueError):f.policy(self.data,'EC-01','edge',**{key:1})
    def test_invalid_node_mode(self):
        for name,mode in [('resolver','edge'),('EC-01','router'),('NG-D01O','host'),('unknown','host')]:
            with self.assertRaises(ValueError):f.policy(self.data,name,mode)
    def test_containment_not_on_another_edge(self):
        with self.assertRaises(ValueError):f.policy(self.data,'EC-02','edge',contain=True)
    def test_ptb_interference_only_fixed_router(self):
        with self.assertRaises(ValueError):f.policy(self.data,'NG-D02O','router',block_ptb=True)
    def test_ra_redirect_denial_is_explicit(self):self.assertIn('icmpv6 type { 134, 137 } counter name control_drop drop',f.policy(self.data,'processor-01','host'))
    def test_foreign_tenant_not_in_edge_allow(self):self.assertNotIn('2001:db8:100:3::10',f.policy(self.data,'EC-01','edge'))
    def counters(self):return {'nftables':[{'counter':{'family':'ip6','table':f.TABLE,'name':n,'packets':0}} for n in f.COUNTERS]}
    def test_complete_counter_readback(self):self.assertEqual(set(f.counter_values(self.counters())),set(f.COUNTERS))
    def test_partial_counter_readback_rejected(self):
        data=self.counters();data['nftables'].pop()
        with self.assertRaises(ValueError):f.counter_values(data)
    def test_boolean_counter_rejected(self):
        data=self.counters();data['nftables'][0]['counter']['packets']=False
        with self.assertRaises(ValueError):f.counter_values(data)
    def test_duplicate_counter_rejected(self):
        data=self.counters();data['nftables'].append(deepcopy(data['nftables'][0]))
        with self.assertRaises(ValueError):f.counter_values(data)


class AddressReadinessTests(unittest.TestCase):
    def setUp(self):self.data=f.load_fixture();self.rows=[{'addr_info':[{'family':'inet6','local':'2001:db8:100:1::10','scope':'global'}]}]
    def test_ready_static_address(self):self.assertTrue(f.ready_addresses(self.data,'processor-01',self.rows))
    def test_empty_not_ready(self):self.assertFalse(f.ready_addresses(self.data,'processor-01',[]))
    def test_tentative_boolean(self):
        self.rows[0]['addr_info'][0]['tentative']=True;self.assertFalse(f.ready_addresses(self.data,'processor-01',self.rows))
    def test_tentative_flag(self):
        self.rows[0]['addr_info'][0]['flags']=['tentative'];self.assertFalse(f.ready_addresses(self.data,'processor-01',self.rows))
    def test_dadfailed(self):
        self.rows[0]['addr_info'][0]['dadfailed']=True;self.assertFalse(f.ready_addresses(self.data,'processor-01',self.rows))
    def test_unexpected_address(self):
        self.rows[0]['addr_info'][0]['local']='2001:db8:100:1::11';self.assertFalse(f.ready_addresses(self.data,'processor-01',self.rows))
    def test_ipv4_empty_interface_rows_are_empty(self):self.assertTrue(f.no_global_ipv4([{'ifname':'lo','addr_info':[]}]))
    def test_ipv4_global_address_not_empty(self):self.assertFalse(f.no_global_ipv4([{'addr_info':[{'family':'inet','scope':'global','local':'192.0.2.1'}]}]))


class DNSMessageTests(unittest.TestCase):
    def test_aaaa(self):q=worker.query(False,'AAAA');self.assertTrue(worker.check_answer(worker.answer(q,False),q))
    def test_a(self):q=worker.query(False,'A');self.assertTrue(worker.check_answer(worker.answer(q,True),q))
    def test_real_wire_truncated_requires_tcp(self):
        q=worker.query(True,'AAAA');self.assertFalse(worker.check_answer(worker.answer(q,False),q));self.assertTrue(worker.check_answer(worker.answer(q,True),q))
    def test_foreign_name_is_nxdomain(self):
        q=dns.message.make_query('other.fixture.invalid','AAAA').to_wire()
        with self.assertRaises(ValueError):worker.check_answer(worker.answer(q,True),q)
    def test_mismatched_transaction(self):
        q=worker.query(False,'AAAA');a=dns.message.from_wire(worker.answer(q,True));a.id=(a.id+1)%65536
        with self.assertRaises(ValueError):worker.check_answer(a.to_wire(),q)
    def test_wrong_data(self):
        q=worker.query(False,'AAAA');a=dns.message.from_wire(worker.answer(q,True));a.answer=[dns.rrset.from_text('small.fixture.invalid.',30,'IN','AAAA','2001:db8:100:2::11')]
        with self.assertRaises(ValueError):worker.check_answer(a.to_wire(),q)
    def test_extra_answer(self):
        q=worker.query(False,'AAAA');a=dns.message.from_wire(worker.answer(q,True));a.answer.append(dns.rrset.from_text('unexpected.fixture.invalid.',30,'IN','AAAA','2001:db8::1'))
        with self.assertRaises(ValueError):worker.check_answer(a.to_wire(),q)
    def test_non_authoritative_reply(self):
        q=worker.query(False,'AAAA');a=dns.message.from_wire(worker.answer(q,True));a.flags&=~dns.flags.AA
        with self.assertRaises(ValueError):worker.check_answer(a.to_wire(),q)
    def test_unsupported_query_type(self):
        with self.assertRaises(ValueError):worker.query(False,'TXT')
    def test_bad_truncation_switch(self):
        with self.assertRaises(ValueError):worker.query(1,'AAAA')
    def test_bad_probe_address_rejected_before_socket(self):
        with patch.object(worker.socket,'socket') as sock,self.assertRaises(ValueError):worker.probe('2001:db9::1')
        sock.assert_not_called()
    def test_excess_payload_refused(self):
        with self.assertRaises(ValueError):worker.probe('2001:db8::1',size=16385)
    def test_host_forwarding_refused(self):
        with patch.object(worker.f,'namespace_guard'),patch.object(worker,'DATA',f.load_fixture()),patch.object(worker,'NODE','resolver'),self.assertRaises(ValueError):worker.configure_forwarding(True)
    def test_forwarding_before_policy_refused(self):
        with patch.object(worker.f,'namespace_guard'),patch.object(worker,'DATA',f.load_fixture()),patch.object(worker,'NODE','NG-D01O'),patch.object(worker,'INSTALLED',False),self.assertRaises(ValueError):worker.configure_forwarding(True)
    def test_no_execute_is_inert(self):
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)/'must-not-exist.json'
            run=subprocess.run([sys.executable,str(f.ROOT/'lab/run_ipv6_lab.py'),'--output',str(out)],capture_output=True,text=True,timeout=10)
            self.assertNotEqual(run.returncode,0);self.assertFalse(out.exists())
    def test_existing_output_never_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)/'record.json';out.write_text('existing')
            run=subprocess.run([sys.executable,str(f.ROOT/'lab/run_ipv6_lab.py'),'--execute','--output',str(out)],capture_output=True,text=True,timeout=10)
            self.assertNotEqual(run.returncode,0);self.assertEqual(out.read_text(),'existing')


if __name__=='__main__':unittest.main()
