#!/usr/bin/env python3
"""GET-only NSX Local Manager config + intent-status readback, no refresh action.

A successful policy GET is not policy realization. This observer sandwiches the
realization query between two revisioned config reads and requires two identical
completed samples. Rules and expression lists retain order. See NATIVE_READBACK.md.
"""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import re
import sys
from urllib.parse import urlencode
if __package__ in (None, ''):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools import readback_core as c

PROFILE = 'nsx-local-policy-v1-selected-fields'
PART = r'[A-Za-z0-9][A-Za-z0-9_-]{0,127}'
PATTERNS = {
 'segment': rf'/infra/segments/{PART}',
 'tier1': rf'/infra/tier-1s/{PART}',
 'static_route': rf'/infra/tier-[01]s/{PART}/static-routes/{PART}',
 'gateway_policy': rf'/infra/domains/{PART}/gateway-policies/{PART}',
 'security_policy': rf'/infra/domains/{PART}/security-policies/{PART}',
 'group': rf'/infra/domains/{PART}/groups/{PART}',
}
TYPES = {'segment':'Segment','tier1':'Tier1','static_route':'StaticRoutes',
         'gateway_policy':'GatewayPolicy','security_policy':'SecurityPolicy','group':'Group'}
FIELDS = {
 'segment': {'connectivity_path','transport_zone_path','subnets','advanced_config','admin_state','type','tags'},
 'tier1': {'tier0_path','route_advertisement_types','route_advertisement_rules','failover_mode','tags'},
 'static_route': {'network','next_hops','tags'},
 'gateway_policy': {'category','sequence_number','stateful','tcp_strict','locked','rules','tags','scope'},
 'security_policy': {'category','sequence_number','stateful','tcp_strict','locked','rules','tags','scope'},
 'group': {'expression','extended_expression','tags'},
}
REQUIRED = {
 'segment': {'connectivity_path','transport_zone_path','subnets','advanced_config'},
 'tier1': {'tier0_path','route_advertisement_types'},
 'static_route': {'network','next_hops'},
 'gateway_policy': {'category','sequence_number','stateful','rules'},
 'security_policy': {'category','sequence_number','stateful','rules'},
 'group': {'expression'},
}
EP = re.compile(rf'/infra/sites/{PART}/enforcement-points/{PART}')
BASE = {'id','path','resource_type','_revision'}
RULE = {'id','action','direction','ip_protocol','logged','disabled','sequence_number',
        'source_groups','destination_groups','sources_excluded','destinations_excluded',
        'services','service_entries','profiles','scope'}


def validate(m):
    c.common_manifest(m, 'nsx')
    if m['profile'] != PROFILE or 'task' in m:
        raise ValueError('Unsupported NSX profile')
    seen=set()
    for r in m['resources']:
        c.exact_keys(r, {'kind','path','expected','realization'})
        kind=r['kind']
        if kind not in PATTERNS or not isinstance(r['path'],str) or not re.fullmatch(PATTERNS[kind], r['path']):
            raise ValueError('Only exact supported Local Manager object paths are accepted')
        if r['path'] in seen:
            raise ValueError('Duplicate resource path')
        seen.add(r['path'])
        e=r['expected']
        c.exact_keys(e, BASE|REQUIRED[kind], FIELDS[kind]-REQUIRED[kind])
        if e['id'] != r['path'].rsplit('/',1)[1] or e['path']!=r['path'] or e['resource_type']!=TYPES[kind]:
            raise ValueError('Expected identity conflicts with selector')
        if type(e['_revision']) is not int or e['_revision']<0:
            raise ValueError('Exact native revision required')
        for flag in ('stateful','tcp_strict','locked'):
            if flag in e and type(e[flag]) is not bool:
                raise ValueError('Boolean policy setting required')
        if 'sequence_number' in e and (type(e['sequence_number']) is not int or e['sequence_number']<0):
            raise ValueError('Integer policy sequence required')
        if 'rules' in e:
            if not isinstance(e['rules'],list) or not 1<=len(e['rules'])<=200:
                raise ValueError('Full selected policy rule list required')
            ids=set(); sequences=set()
            for rule in e['rules']:
                if not isinstance(rule,dict) or not RULE<=rule.keys():
                    raise ValueError('Rule identity, order and security fields required')
                c.identifier(rule['id'])
                if any(type(rule[k]) is not bool for k in ('logged','disabled','sources_excluded','destinations_excluded')) or type(rule['sequence_number']) is not int:
                    raise ValueError('Typed rule flags and sequence required')
                if rule['action'] not in ('ALLOW','DROP','REJECT') or rule['direction'] not in ('IN','OUT','IN_OUT') or rule['ip_protocol'] not in ('IPV4','IPV6','IPV4_IPV6'):
                    raise ValueError('Unsupported rule semantics')
                for key in ('source_groups','destination_groups','services','scope'):
                    if not isinstance(rule[key],list) or not rule[key] or any(not isinstance(v,str) or not v for v in rule[key]):
                        raise ValueError('Explicit nonempty rule membership required')
                if rule['sequence_number']<0 or rule['sequence_number'] in sequences:
                    raise ValueError('Nonnegative unique rule sequence required')
                for key in ('service_entries','profiles'):
                    if not isinstance(rule[key],list):
                        raise ValueError('Explicit inline service/profile list required')
                if rule['id'] in ids:
                    raise ValueError('Duplicate rule identity')
                ids.add(rule['id']); sequences.add(rule['sequence_number'])
        z=r['realization']
        c.exact_keys(z, {'intent_version','enforcement_points'})
        c.text(z['intent_version'], 'separately recorded intent version', 128)
        eps=z['enforcement_points']
        if not isinstance(eps,list) or not 1<=len(eps)<=20 or any(not isinstance(p,str) or not EP.fullmatch(p) for p in eps) or len(set(eps))!=len(eps):
            raise ValueError('Exact nonduplicate enforcement-point coverage required')


def status_target(path):
    return '/policy/api/v1/infra/realized-state/status?' + urlencode({'intent_path':path})


def targets(m):
    validate(m)
    return {t for r in m['resources'] for t in ('/policy/api/v1'+r['path'],status_target(r['path']))}


def progress(body, r):
    if body.get('intent_path')!=r['path']:
        return 'UNKNOWN','REALIZATION_IDENTITY_MISMATCH',None
    version=body.get('intent_version')
    if not isinstance(version,str):
        return 'UNKNOWN','REALIZATION_VERSION_MISSING',None
    # No assumption that intent_version equals the config _revision.
    if version!=r['realization']['intent_version']:
        return 'PENDING','REALIZATION_VERSION_NOT_EXPECTED',None
    consolidated=body.get('consolidated_status')
    overall=consolidated.get('consolidated_status') if isinstance(consolidated,dict) else None
    publication=body.get('publish_status')
    points=body.get('consolidated_status_per_enforcement_point')
    if not isinstance(points,list) or not points:
        return 'UNKNOWN','REALIZATION_SPAN_MISSING',None
    selected=[];seen=set()
    for point in points:
        if not isinstance(point,dict):
            return 'UNKNOWN','INVALID_REALIZATION_SPAN',None
        name=point.get('enforcement_point_path'); value=point.get('consolidated_status')
        state=value.get('consolidated_status') if isinstance(value,dict) else None
        if not isinstance(name,str) or not EP.fullmatch(name) or name in seen:
            return 'UNKNOWN','INVALID_REALIZATION_SPAN',None
        seen.add(name);selected.append({'path':name,'state':state})
    if seen!=set(r['realization']['enforcement_points']):
        return 'UNKNOWN','REALIZATION_SPAN_DIFFERS',None
    states=[overall]+[p['state'] for p in selected]
    if publication=='ERROR' or 'ERROR' in states:
        return 'FAILED','REALIZATION_ERROR',None
    if publication not in ('REALIZED','UNREALIZED','UNAVAILABLE') or any(v not in ('SUCCESS','PENDING','UNKNOWN') for v in states):
        return 'UNKNOWN','UNRECOGNIZED_REALIZATION_STATUS',None
    if publication=='UNAVAILABLE' or 'UNKNOWN' in states:
        return 'UNKNOWN','REALIZATION_STATUS_UNKNOWN',None
    selected.sort(key=lambda p:p['path'])
    observation={'intent_version':version,'publish_status':publication,'overall':overall,'points':selected}
    if publication=='REALIZED' and all(v=='SUCCESS' for v in states):
        return 'COMPLETE','EXPECTED_REALIZATION_REPORTED',c.digest(observation)
    return 'PENDING','REALIZATION_PENDING',c.digest(observation)


def realization_witness(body):
    """Keep only bounded attribution/status fields; omit alarms and diagnostic text."""
    def scalar(value): return value if isinstance(value, str) and len(value) <= 1024 else None
    def status(value): return {'consolidated_status': scalar(value.get('consolidated_status'))} if isinstance(value, dict) else None
    points = body.get('consolidated_status_per_enforcement_point')
    return dict(intent_path=scalar(body.get('intent_path')), intent_version=scalar(body.get('intent_version')),
        publish_status=scalar(body.get('publish_status')), consolidated_status=status(body.get('consolidated_status')),
        consolidated_status_per_enforcement_point=[dict(enforcement_point_path=scalar(p.get('enforcement_point_path')),
            consolidated_status=status(p.get('consolidated_status'))) if isinstance(p, dict) else None for p in points]
            if isinstance(points, list) and len(points) <= 20 else None)


def validate_observation_history(m, history, states, current=None):
    """Recompute realization and refuse matching summaries contradicted by either read."""
    from tools.run_files import require
    try:
        if len(states) == 1 and states[0].get('resource_key') == 'scope':
            require(states[0].get('config_status') == states[0].get('progress') == 'UNKNOWN', 'Invalid scope hold')
            return
        require([s.get('resource_key') for s in states] == [r['path'] for r in m['resources']], 'NSX coverage differs')
        for r, state in zip(m['resources'], states):
            witness = state['config_witness']
            c.exact_keys(witness, {'before_sha256', 'after_sha256', 'identity_match', 'revision'})
            require(all(isinstance(witness[k], str) and c.HEX.fullmatch(witness[k])
                        for k in ('before_sha256', 'after_sha256')), 'Invalid NSX snapshot digest')
            require(type(witness['identity_match']) is bool and witness['identity_match'] is state.get('identity_match')
                    and c.digest(witness['revision']) == c.digest(state.get('revision'))
                    and witness['after_sha256'] == state.get('config_sha256'), 'NSX snapshot summary differs')
            native = state['realization_witness']
            require(c.digest(realization_witness(native)) == c.digest(native), 'Invalid realization witness shape')
            p, reason, realized = progress(native, r)
            if witness['before_sha256'] != witness['after_sha256']:
                require(state.get('config_status') == 'UNKNOWN', 'Changed configuration cannot match')
                p, reason = 'UNKNOWN', 'CONFIG_CHANGED_DURING_REALIZATION_READ'
            if not witness['identity_match']:
                require(state.get('config_status') == 'UNKNOWN', 'Foreign identity cannot match')
                p, reason = 'UNKNOWN', 'RESOURCE_IDENTITY_MISMATCH'
            require(state.get('progress') == p and state.get('reason') == reason
                    and state.get('realization_sha256') == realized, 'Realization summary contradicts witness')
            if state.get('config_status') == 'MATCH':
                require(witness['identity_match'] and state.get('mismatch_fields') == []
                        and witness['before_sha256'] == witness['after_sha256'] == c.digest(r['expected'])
                        and type(witness['revision']) is int and witness['revision'] == r['expected']['_revision'],
                        'NSX match contradicts accepted snapshots')
    except (ValueError, TypeError, KeyError, IndexError, AttributeError):
        raise c.ObservationError('NSX_OBSERVATION_WITNESS_INVALID') from None


def sample(m, client):
    result=[]
    for r in m['resources']:
        before,_=client.get('/policy/api/v1'+r['path'])
        realization,_=client.get(status_target(r['path']))
        after,_=client.get('/policy/api/v1'+r['path'])
        fields=set(r['expected'])
        a={k:before[k] for k in fields if k in before}
        b={k:after[k] for k in fields if k in after}
        mismatch=c.differences(b,r['expected'])
        config='UNKNOWN' if any(s.endswith(':missing') for s in mismatch) else ('DIFFERENT' if mismatch else 'MATCH')
        realization = realization_witness(realization)
        p,reason,realized=progress(realization,r)
        if c.digest(a)!=c.digest(b):
            config='UNKNOWN';p='UNKNOWN';reason='CONFIG_CHANGED_DURING_REALIZATION_READ'
        identity=not c.differences(b,{k:r['expected'][k] for k in ('id','path','resource_type')})
        if not identity:
            config='UNKNOWN';p='UNKNOWN';reason='RESOURCE_IDENTITY_MISMATCH'
        result.append({'resource_key':r['path'],'identity_match':identity,
            'config_status':config,'progress':p,'reason':reason,'mismatch_fields':mismatch,
            'config_sha256':c.digest(b),'revision':b.get('_revision') if type(b.get('_revision')) is int else None,
            'realization_sha256':realized, 'realization_witness':realization,
            'config_witness':dict(before_sha256=c.digest(a), after_sha256=c.digest(b), identity_match=identity,
                                  revision=b.get('_revision') if type(b.get('_revision')) is int else None)})
    return result


def main():
    from tools.readback_cli import run
    return run(sys.modules[__name__], 'NSXT')

if __name__=='__main__':raise SystemExit(main())
