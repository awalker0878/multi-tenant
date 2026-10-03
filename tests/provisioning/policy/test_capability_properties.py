"""Semantic requirements are not feature flags or vendor-family equivalence."""
from __future__ import annotations

import copy
from dataclasses import replace
import unittest

from provisioner.domain.capabilities import CAPABILITIES
from provisioner.domain.capability_properties import (
    PROPERTY_VALUES, PropertyRequirement as Requirement, entails, evaluate,
    merge_requirements, parse_requirements, validate_observations,
)
from provisioner.domain.errors import ProvisioningError
from provisioner.execution.plan import create_plan
from provisioner.inventory.model import build, FIXTURE
from provisioner.portability import policy, policy_translation
from provisioner.profiles.loader import load_catalogs
from tests.provisioning import support
from tests.provisioning.policy.test_profile_versions import edited_catalogs, _edit


def req(name, value, operator='eq'):
    return Requirement(name, operator, value)


class PropertyContractTests(unittest.TestCase):
    def test_all_properties_use_existing_unique_capability_owners(self):
        self.assertEqual(len(CAPABILITIES), 97)
        self.assertTrue(all(key.split('.')[0] in CAPABILITIES for key in PROPERTY_VALUES))
        with self.assertRaises(TypeError):
            PROPERTY_VALUES['new.flag'] = (True,)

    def test_all_declared_value_types_are_enforced(self):
        for name, values in PROPERTY_VALUES.items():
            values = values if values is not None else (0, 2**63-1)
            for value in values:
                with self.subTest(name=name, value=value):
                    requirement = req(name, value)
                    self.assertTrue(requirement.satisfied_by(value))
                    self.assertNotIn('PROPERTY_MISMATCH:' + name, evaluate((requirement,), {name:value}))
            for bad in (None, {}, [], 1.5, float('inf')):
                with self.subTest(name=name, bad=bad), self.assertRaises(ValueError):
                    req(name, bad)

    def test_booleans_do_not_count_as_integer_observations(self):
        for bad in (True, -1, 2**63):
            with self.assertRaises(ValueError):
                validate_observations({'network_domain.mtu':bad})
        with self.assertRaises(ValueError):
            validate_observations({'huge_pages.configured':1})

    def test_unknown_is_not_false_or_a_default(self):
        requirement = req('secure_boot.enabled', False)
        self.assertEqual(evaluate((requirement,), {}), ('PROPERTY_UNKNOWN:secure_boot.enabled',))
        self.assertEqual(evaluate((requirement,), {'secure_boot.enabled':False}), ())

    def test_enum_mismatch_is_not_cross_platform_equivalence(self):
        requirement=req('distributed_firewall.rule_model', 'ordered-first-match')
        self.assertEqual(evaluate((requirement,), {
            'distributed_firewall.rule_model':'additive-allow'}),
            ('PROPERTY_MISMATCH:distributed_firewall.rule_model',))

    def test_qos_ceiling_never_means_minimum_iops(self):
        requirement=req('storage_qos.minimum_iops', 1000, 'gte')
        self.assertEqual(evaluate((requirement,), {'storage_qos.maximum_iops':10000}),
                         ('PROPERTY_UNKNOWN:storage_qos.minimum_iops',))
        self.assertTrue(evaluate((requirement,), {'storage_qos.minimum_iops':999}))
        self.assertFalse(evaluate((requirement,), {'storage_qos.minimum_iops':1000}))

    def test_requirement_union_cannot_weaken_or_contradict_profiles(self):
        low=req('network_domain.mtu',1500,'gte');high=req('network_domain.mtu',9000,'gte')
        self.assertEqual(merge_requirements((low,), (high,)), merge_requirements((high,), (low,)))
        self.assertTrue(evaluate(merge_requirements((low,), (high,)), {'network_domain.mtu':1500}))
        with self.assertRaises(ValueError):
            merge_requirements((high,), (req('network_domain.mtu',1500,'lte'),))
        with self.assertRaises(ValueError):
            merge_requirements((req('secure_boot.enabled',True),), (req('secure_boot.enabled',False),))

    def test_stronger_requirements_entail_weaker_but_not_the_reverse(self):
        low=req('storage_qos.minimum_iops',1000,'gte');high=req('storage_qos.minimum_iops',2000,'gte')
        self.assertTrue(entails((high,),low));self.assertFalse(entails((low,),high))
        self.assertFalse(entails((),low))
        self.assertTrue(entails((req('network_domain.mtu',1500,'gte'),
                                 req('network_domain.mtu',1500,'lte')),req('network_domain.mtu',1500)))

    def test_observations_are_copied_and_immutable(self):
        original={'secure_boot.enabled':True};frozen=validate_observations(original)
        original['secure_boot.enabled']=False
        self.assertTrue(frozen['secure_boot.enabled'])
        with self.assertRaises(TypeError): frozen['secure_boot.enabled']=False

    def test_closed_requirement_schema_rejects_typos_owner_drift_and_duplicates(self):
        row=req('secure_boot.enabled', True).to_dict()
        for value,caps in (([row],[]),([row,row],['secure_boot']),
                           ([{**row,'override':True}],['secure_boot']),
                           ([{**row,'property':'secure_boot.enable'}],['secure_boot']),
                           ([{**row,'operator':'gte'}],['secure_boot']),
                           ([row]*129,['secure_boot'])):
            with self.subTest(value=value[:1]),self.assertRaises(ValueError):
                parse_requirements(value,caps)

    def test_conditional_native_constraints_do_not_use_family_guesses(self):
        self.assertEqual(evaluate((),{}),())
        observed={'network_domain.routing_model':'nsx-tier0-vrf'}
        self.assertIn('PROPERTY_UNKNOWN:network_domain.parent_ha_mode',evaluate((),observed))
        observed['network_domain.parent_ha_mode']='active-active-stateful'
        self.assertIn('NSX_VRF_PARENT_HA_INCOMPATIBLE',evaluate((),observed))
        for mode in ('active-standby','active-active-stateless'):
            observed['network_domain.parent_ha_mode']=mode
            self.assertEqual(evaluate((),observed),())

    def test_dpdk_requires_pages_and_all_nic_security_cannot_bypass(self):
        observed={'network_qos.datapath':'ovs-dpdk','huge_pages.configured':False}
        self.assertIn('OVS_DPDK_HUGE_PAGES_REQUIRED',evaluate((),observed))
        observed['huge_pages.configured']=True
        self.assertEqual(evaluate((),observed),())
        self.assertIn('DISTRIBUTED_FIREWALL_DATAPATH_BYPASS', evaluate((),{
            'distributed_firewall.scope':'all-workload-nics','sriov_nic.security_path':'bypass'}))


class PropertyIntegrationTests(unittest.TestCase):
    def test_real_profiles_enforce_scoped_properties_on_all_three_platforms(self):
        for platform in support.PLATFORMS:
            with self.subTest(platform=platform):
                plan=support.platform_plan(platform)
                self.assertTrue(plan.resolution.capability_constraints)
                self.assertFalse(plan.native_contact)
                document=support.reference_fixture(platform).to_dict()
                for site in document['sites']:
                    for cell in site['cells']:
                        for cluster in cell['clusters']:
                            cluster['capability_properties'].pop('gateway_policy.default_action')
                with self.assertRaises(ProvisioningError) as caught:
                    create_plan(support.platform_request(platform), '<properties-test>',
                                build(document), support.catalogs())
                self.assertEqual(caught.exception.code,'NO_ELIGIBLE_PLACEMENT')

    def test_one_qualifying_cluster_cannot_supply_other_clusters_missing_facts(self):
        from provisioner.placement import resolver
        from tests.provisioning.placement.test_placement import inventory_document, request
        document=inventory_document(status=FIXTURE)
        clusters=document['sites'][0]['cells'][0]['clusters']
        clusters[0]['capability_properties']={'network_domain.routing_isolation':'independent-context'}
        result=resolver.place(replace(request(zones=('OZ','RZ')), capability_constraints=(
            req('network_domain.routing_isolation','independent-context'),)), build(document))
        self.assertNotEqual(result.status,'PLACED')

    def test_invented_profile_requirements_are_rejected_not_ignored(self):
        with self.assertRaises(ProvisioningError):
            edited_catalogs(lambda root:_edit(root/'security/catalog.json', lambda d:
                d['profiles'][0]['requires'].__setitem__('automatic_native_qualification',True)))

    def test_profile_conflicts_are_rejected_before_placement(self):
        from provisioner.profiles.resolver import resolve
        from provisioner.compiler.normalize import normalize
        catalog=edited_catalogs(lambda root:_edit(root/'network/catalog.json',lambda d:
            d['profiles'][0]['requires'].__setitem__('constraints',[
                req('network_domain.routing_isolation','shared-context').to_dict()])))
        request=normalize(support.reference_document(),source='<test>',catalog=catalog)
        with self.assertRaises(ProvisioningError): resolve(request.spec,catalog)

    def test_capsule_preserves_requirements_and_rejects_legacy_format(self):
        source=support.platform_plan('openstack');target=support.platform_plan('nutanix')
        capsule=policy.build(source)
        self.assertEqual(capsule['requirements']['capability_constraints'],
                         [r.to_dict() for r in source.resolution.capability_constraints])
        reduced=replace(target,resolution=replace(target.resolution,capability_constraints=()))
        result=policy_translation.compile(capsule,reduced)
        self.assertTrue(any(code.startswith('SOURCE_PROPERTY_NOT_ENFORCED') for code in result['blockers']))
        self.assertFalse(result['qualified'])
        old=copy.deepcopy(capsule);old['format']='hosting-portable-policy-capsule/1'
        with self.assertRaises(ValueError):policy_translation.compile(old,target)

    def test_changed_property_is_bound_into_plan_and_inventory_identity(self):
        original=support.reference_fixture('openstack')
        changed=original.to_dict()
        cluster=changed['sites'][0]['cells'][0]['clusters'][0]
        cluster['capability_properties']['distributed_firewall.enforcement']='monitor'
        self.assertNotEqual(original.reference['digest'],build(changed).reference['digest'])
        plan=support.platform_plan('openstack')
        self.assertEqual(plan.resolution.format,'hosting-profile-resolution/3')
        self.assertTrue(plan.resolution.to_dict()['capability_constraints'])


if __name__=='__main__': unittest.main()
