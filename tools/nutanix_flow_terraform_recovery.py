"""Bind held existing Flow service changes to sealed intent and activity evidence.

Generated service-rule IDs are observed subresources, never policy adoption.
The two retained denies and any retained service IDs must remain known and exact.
"""
from copy import deepcopy
from tools import readback_core as c, lifecycle_transition as lifecycle, nutanix_flow_activity_observe as activity
from tools import nutanix_flow_observe as flow
from tools.nutanix_terraform_recovery import valid_mask
from tools.plan_review import has_true
from tools.run_files import require

OBSERVED_PLAN_FIELDS = {'id', 'ext_id', 'name', 'type', 'state', 'scope', 'vpc_reference',
                        'is_hitlog_enabled', 'is_ipv6_traffic_allowed', 'rules'}
COMPUTED_FIELDS = {'last_update_time'}


def bind_rules(change, expected):
    before, after = change['before'], change['after']
    unknown = deepcopy(change.get('after_unknown', {}))
    require(valid_mask(unknown), 'Malformed Flow unknown mask')
    mask = unknown.get('rules', [])
    require(mask is False or isinstance(mask, list) and (not mask or len(mask) == len(after['rules'])),
            'Incomplete rule unknown mask')
    planned = deepcopy(after)
    for index, rule in enumerate(after['rules']):
        ident = expected['rules'][index]['ext_id']
        rule_mask = mask[index] if mask and isinstance(mask, list) else {}
        require(isinstance(rule_mask, dict), 'Rule unknown object required')
        old = before['rules'][index] if index < len(before['rules']) else None
        retained = old is not None and (index < 2 or old.get('description') == rule.get('description'))
        if retained:
            require(old.get('ext_id') == rule.get('ext_id') == ident and not has_true(rule_mask.get('ext_id')),
                    'Retained Flow rule identity differs or is unresolved')
        elif rule_mask.get('ext_id') is True:
            require(rule.get('ext_id') is None, 'Generated rule ID contradicts unknown mask')
            planned['rules'][index]['ext_id'] = ident
            rule_mask.pop('ext_id')
        else:
            require(rule.get('ext_id') == ident, 'Known service-rule identity differs')
    require(not any(has_true(v) for k, v in unknown.items() if k not in COMPUTED_FIELDS), 'Unresolved Flow configuration')
    require(not c.differences(planned, expected), 'Planned Flow configuration differs from native expectations')


def bind_plan(plan, inputs, manifest, transition, *, attempted_at):
    require(manifest.get('profile') == activity.PROFILE, 'Flow task activity required; snapshot-only recovery is unsupported')
    activity.validate(manifest)
    require(plan.get('format_version') == '1.2' and plan.get('complete') is True and not plan.get('errored')
            and not plan.get('deferred_changes') and not plan.get('resource_drift')
            and all(isinstance(check, dict) and check.get('status') == 'pass' for check in plan.get('checks', [])),
            'Unresolved saved plan')
    require(transition['scope']['platform'] == 'nutanix' and transition['scope']['phase'] == 'domains'
            and c.digest(transition['requested_inputs']) == c.digest(inputs), 'Flow lifecycle scope or inputs differ')
    lifecycle.plan_bindings(plan, transition, as_of=c.timestamp(attempted_at))
    wanted = transition['resources']; resources = {r['ext_id']: r for r in manifest['resources']}; actual = {}; ids = set()
    for item in plan['resource_changes']:
        change = item['change']; unknown = change.get('after_unknown', {})
        require(valid_mask(unknown), 'Malformed planned unknown mask')
        if item['address'] not in wanted:
            # Domain plans also contain the existing category, VPC and subnet.
            # lifecycle.plan_bindings requires exact no-ops for every such item.
            require(not has_true(unknown), 'Unresolved unrelated native resource')
            continue
        require(item.get('provider_name') == 'registry.terraform.io/nutanix/nutanix', 'Unreviewed Flow provider')
        spec = wanted[item['address']]; ident = spec['id']
        require(ident in resources and ident not in ids, 'Flow plan and observation coverage differ')
        r = resources[ident]; member = inputs['members'][spec['member']]
        native = transition['prior_outputs']['members']['value'][spec['member']]
        services = lifecycle.service_rules(member) if transition['target_stage'] == 'bootstrap' else {}
        require(r['category_id'] == native['security_category_id'] and r['vpc_id'] == native['vpc_id']
                and c.digest(r['services']) == c.digest(services), 'Policy expectations differ from sealed domain intent')
        name = inputs['tenant_key'] + '-' + spec['member'] + '-quarantine'
        require(r['expected']['name'] == name, 'Policy name differs from owned domain')
        expected = flow.policy_shape(r['expected'], r) | dict(id=ident, ext_id=ident, name=name)
        require(change['before'].get('id') == change['after'].get('id') == ident, 'Existing policy identity required')
        if change['actions'] == ['no-op']: lifecycle.unchanged(change['before'], change['after'], COMPUTED_FIELDS)
        bind_rules(change, expected)
        for field, value in [('tenant_id', r['expected']['tenantId']), ('secured_groups', [r['category_id']]),
                             ('is_system_defined', False), ('is_ipv4_address_scope', True), ('is_ipv6_address_scope', False)]:
            if field in change['after']:
                require(not c.differences(change['after'][field], value), 'Known Flow metadata contradicts native ownership')
        ids.add(ident); actual[item['address']] = ident
    require(set(actual) == set(wanted) and ids == set(resources), 'Incomplete Flow plan or observation scope')
    return actual
