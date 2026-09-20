"""Exact Terraform Flow rule validation for the owned restricted policy."""
from tools import readback_core as c
from tools.run_files import require

ALTERNATE_SPECS = {'two_env_isolation_rule_spec', 'multi_env_isolation_rule_spec',
                   'application_rule_spec', 'intra_entity_group_rule_spec'}
EMPTY_APPLICATION = {'secured_group_entity_group_reference', 'src_entity_group_reference',
    'dest_entity_group_reference', 'src_category_references', 'dest_category_references',
    'src_subnet', 'dest_subnet', 'src_address_group_references', 'dest_address_group_references',
    'service_group_references', 'tcp_services', 'udp_services', 'icmp_services',
    'network_function_chain_reference', 'network_function_reference'}
EMPTY_INTRA = {'secured_group_entity_group_reference', 'secured_group_service_references',
               'tcp_services', 'udp_services', 'icmp_services'}


def shape(actual, expected, empty=frozenset(), metadata=frozenset()):
    require(isinstance(actual, dict) and not c.differences(actual, expected), 'Flow policy differs from exact intent')
    for key in actual.keys() - expected.keys():
        require(key in metadata or key in empty and (actual[key] is None or actual[key] == '' or actual[key] == []),
                'Unreviewed Flow selector or behavior')


def rule_spec(rule, kind, description=None):
    spec_name = 'application_rule_spec' if kind == 'APPLICATION' else 'intra_entity_group_rule_spec'
    expected = {'type': kind}
    if description is not None: expected['description'] = description
    require(isinstance(rule, dict) and isinstance(rule.get('spec'), list) and len(rule['spec']) == 1, 'Single Flow rule specification required')
    shape(rule, expected | {'spec': rule['spec']}, metadata={'ext_id', 'description'} if description is None else {'ext_id'})
    spec = rule['spec'][0]
    require(isinstance(spec, dict) and isinstance(spec.get(spec_name), list) and len(spec[spec_name]) == 1, 'Flow rule union differs')
    shape(spec, {spec_name: spec[spec_name]}, empty=ALTERNATE_SPECS - {spec_name})
    return spec[spec_name][0]


def validate(after, category, vpc, services):
    require(after.get('type') == 'APPLICATION' and after.get('state') == 'ENFORCE'
            and after.get('scope') == 'VPC_LIST' and after.get('vpc_reference') == [vpc]
            and after.get('is_hitlog_enabled') is True and after.get('is_ipv6_traffic_allowed') is False,
            'Mandatory Flow policy boundary changed')
    rules = after.get('rules')
    require(isinstance(rules, list) and len(rules) == 2 + len(services), 'Exact baseline and service rules required')
    group = {'secured_group_category_associated_entity_type': 'VM', 'secured_group_category_references': [category]}
    application = group | {'src_allow_spec': 'NONE', 'dest_allow_spec': 'NONE'}
    baseline = rule_spec(rules[0], 'APPLICATION')
    for key in ('src_category_associated_entity_type', 'dest_category_associated_entity_type'):
        if key in baseline: require(baseline[key] == 'VM', 'Unexpected category entity type')
    if 'is_all_protocol_allowed' in baseline:
        require(baseline['is_all_protocol_allowed'] is None or type(baseline['is_all_protocol_allowed']) is bool, 'Invalid baseline protocol flag')
    shape(baseline, application, EMPTY_APPLICATION,
          {'src_category_associated_entity_type', 'dest_category_associated_entity_type', 'is_all_protocol_allowed'})
    shape(rule_spec(rules[1], 'INTRA_GROUP'), group | {'secured_group_action': 'DENY'}, EMPTY_INTRA)
    for rule, (name, service) in zip(rules[2:], sorted(services.items())):
        side = 'src' if service['direction'] == 'ingress' else 'dest'
        expected = application | {'src_category_associated_entity_type': 'VM', 'dest_category_associated_entity_type': 'VM',
            'is_all_protocol_allowed': False, side + '_subnet': [{'value': service['remote_ipv4'], 'prefix_length': 32}],
            service['protocol'] + '_services': [{'start_port': service['port'], 'end_port': service['port']}]}
        actual = rule_spec(rule, 'APPLICATION', name)
        shape(actual, expected, EMPTY_APPLICATION)
        # Selected nested shapes must not conceal extra peer/protocol selectors.
        for key in (side + '_subnet', service['protocol'] + '_services'):
            shape(actual[key][0], expected[key][0])
