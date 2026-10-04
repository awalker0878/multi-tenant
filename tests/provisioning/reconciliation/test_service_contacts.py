"""Selected dynamic service contracts over real signed loopback DNS.

The B10 enrollment in this fixture is a test double; the TCP/TSIG packets use
the real DNS owner. It establishes no installed DNS/Vault/native qualification.
"""
from copy import deepcopy
from datetime import timedelta
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import dns.update

from provisioner.controlplane.reconciliation.service_runtime import require_service_credentials
from provisioner.controlplane.reconciliation.service_propagation import (
    EnrolledDnsPropagationContext,EnrolledDnsPropagationRuntime,view_binding)
from provisioner.controlplane.worker.command_runtime import SelectedWorkerCommandAuthority
from provisioner.controlplane.worker.vault_consumer import ConsumedVaultCredential
from provisioner.execution import dns_propagation
from provisioner.execution.run_files import digest,utcnow
from tests import test_dns_propagation as dns_fixture


class EnrolledServiceContactTests(unittest.TestCase):
    def test_each_service_role_rejects_unselected_extra_native_credentials(self):
        for kind,keys,reader in (('ipam',{'netbox'},False),('dns',{'dns','netbox'},False),
                                ('dns_cutover',{'dns'},True),('openstack_quota',{'quota'},False)):
            selected={'format':'hosting-selected-services-credential/1'}|{key:{} for key in keys}
            require_service_credentials(selected,kind,reader=reader)
            with self.subTest(kind=kind),self.assertRaises(ValueError):
                require_service_credentials(selected|{'root_native_password':'forbidden'},kind,reader=reader)
        with self.assertRaises(ValueError):
            require_service_credentials({'format':'hosting-selected-services-credential/1','netbox':{}},'dns')


class EnrolledDnsContactTests(unittest.TestCase):
    def setUp(self):
        self.fixture=dns_fixture.PropagationTests(); self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.calls=0; self.revoked=False
        self.grant=SimpleNamespace(operation_kind='DISCOVER_READ')
        self.runtime=object.__new__(EnrolledDnsPropagationRuntime)
        self.runtime.command_runtime=SimpleNamespace(grant=self.grant)
        self.authority=object.__new__(SelectedWorkerCommandAuthority)
        def current():
            self.calls+=1
            if self.revoked: raise ValueError('Synthetic read grant revoked')
            return self.grant,utcnow()+timedelta(minutes=2)
        self.authority.require_current=current
        self.data={'format':'hosting-selected-dns-views-credential/1','dns_views':{
            target['id']:{'format':'hosting-dns-dynamic-view/1',
                          'binding_digest':view_binding(target,self.fixture.job,self.fixture.scope),
                          'secret':self.fixture.keys[target['id']]} for target in self.fixture.config['targets']}}

    def context(self,config=None,data=None):
        material=ConsumedVaultCredential(data or self.data,utcnow()+timedelta(minutes=1),'a'*64,'vault:synthetic-views')
        return EnrolledDnsPropagationContext(self.runtime,self.authority,material,
            config or self.fixture.config,self.fixture.job,self.fixture.scope,self.fixture.receipt)

    def observe(self,context):
        original=dns_propagation.validate
        # The installed owner prohibits loopback. Only this synthetic validation
        # port admits the laboratory listener; all actual signed contacts remain.
        def fixture_validate(*args,**kwargs): return original(*args,**(kwargs|{'fixture':True}))
        with patch.object(dns_propagation,'validate',side_effect=fixture_validate):
            return dns_propagation.observe(context.effective,self.fixture.job,self.fixture.scope,
                self.fixture.receipt,context.secrets,enrolled_context=context)

    def test_refreshes_only_authentication_and_checks_original_read_grant_each_real_exchange(self):
        config=deepcopy(self.fixture.config)
        for target in config['targets']: target['tsig_sha256']='0'*64
        context=self.context(config)
        self.assertEqual(context.original,config)
        for old,fresh in zip(config['targets'],context.effective['targets']):
            self.assertEqual({key:value for key,value in old.items() if key!='tsig_sha256'},
                             {key:value for key,value in fresh.items() if key!='tsig_sha256'})
            self.assertEqual(fresh['tsig_sha256'],digest(self.fixture.keys[fresh['id']].encode()))
        result=self.observe(context)
        self.assertEqual(len(result['observations']),6)
        self.assertGreater(self.calls,12)
        self.assertEqual([server.update_requests for server in self.fixture.servers],[1,0,0])

    def test_wrong_view_binding_or_changed_effective_endpoint_is_rejected_before_contact(self):
        data=deepcopy(self.data); data['dns_views']['secondary']['binding_digest']='b'*64
        before=[server.queries for server in self.fixture.servers]
        with self.assertRaises(ValueError): self.context(data=data)
        context=self.context(); context.effective['targets'][1]['port']+=1
        with self.assertRaises(ValueError): self.observe(context)
        self.assertEqual([server.queries for server in self.fixture.servers],before)

    def test_revoked_reader_stops_after_exchange_and_never_sends_dns_update(self):
        context=self.context(); server=self.fixture.servers[0]; original=server.respond
        def revoke(message):
            self.revoked=True
            return original(message)
        with patch.object(server,'respond',side_effect=revoke),self.assertRaisesRegex(ValueError,'revoked'):
            self.observe(context)
        self.assertEqual([server.update_requests for server in self.fixture.servers],[1,0,0])
        self.revoked=False
        client=context.client(context.effective['targets'][0],context.effective,time.monotonic()+10)
        with self.assertRaisesRegex(ValueError,'UPDATE'):
            client.exchange(dns.update.Update(self.fixture.job['zone']))

