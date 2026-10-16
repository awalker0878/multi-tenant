"""Execute current-authority and cross-tenant denials through live Planning."""
import hashlib
import json
import os
import uuid


def security_probes(c, calls, base, application, environment, protected):
    from assurance import inventory, operation_key
    operations = {op['key']: op for op in inventory(c['root'])['operations']}
    tenant, foreign = c['fixture']['tenant'], c['fixture']['foreign_tenant']
    # Audit writes in Governance are legitimate authentication activity. These
    # snapshots cover every Planning-owned relation, including command receipts,
    # immutable plans, deliveries, projections and qualification authority.
    tables = c['sql']("SELECT tablename FROM pg_tables WHERE schemaname='app' ORDER BY tablename;", 'planning').splitlines()
    if not tables or any(not name.replace('_', '').isalnum() for name in tables):
        raise RuntimeError('planning_state_inventory_missing')

    def state():
        return [(table, c['sql']("SELECT md5(coalesce(jsonb_agg(to_jsonb(t) ORDER BY to_jsonb(t)::text)::text,'[]')) FROM app."+table+' t;', 'planning'))
                for table in tables]

    def grant(call, wrong_scope=False):
        tokens = []
        action = 'plan.create' if call['method'] == 'POST' and call['tail'] in {'assessments', 'plans'} else 'plan.read'
        for site in dict.fromkeys(call['sites']):
            reply = c['gov']('/v1/tenants/'+tenant+'/actor-delegations', {'audience': 'planning', 'action': action,
                'scope': {'site_id': site, 'environment': environment,
                          'resource_id': str(uuid.uuid4()) if wrong_scope else application}}, token=c['fixture']['author_token'])
            c['private_values'].append(reply['delegation_token'])
            tokens.append(site+':'+reply['delegation_token'])
        return {'Authorization': 'Bearer '+c['credentials']['console-planning'][0],
                'X-Planning-Delegations': ','.join(tokens),
                **({'Idempotency-Key': call['key']} if call['key'] else {})}

    rows = []
    for call in calls:
        path = base+'/'+call['tail']
        body = call['body'] if call['method'] == 'POST' else None
        positive = c['wire']('https://127.0.0.1:8446', path, call['method'], body, grant(call))
        c['check']('p05-security-positive-'+call['method']+'-'+call['tail'], positive[0] == call['status'])
        for kind, target, headers in [
            ('wrong-scope', path, grant(call, wrong_scope=True)),
            ('cross-tenant', path.replace('/tenants/'+tenant+'/', '/tenants/'+foreign+'/'), grant(call)),
        ]:
            before = state()
            reply = c['wire']('https://127.0.0.1:8446', target, call['method'], body, headers)
            measured = c['conformance'].rows[-1]
            after = state()
            disclosed = any(value in json.dumps(reply[1]) for value in protected)
            c['check']('p05-security-'+kind+'-'+call['method']+'-'+call['tail'],
                reply[0] in (403, 404) and not disclosed and before == after
                and measured['request_valid'] is True and measured['response_valid'] is True
                and measured['owner'] == 'planning' and measured['path'] == call['path'])
            op = operations[operation_key('planning', call['method'], call['path'])]
            rows.append({'key': op['key'], 'claim': 'authorization' if kind == 'wrong-scope' else 'tenant_isolation',
                'source': 'live-denial', 'result': 'PASS', 'release_sha256': op['release_sha256'],
                'test': 'scripts/p05/planning_security.py:security_probes', 'denial_kind': kind,
                'authenticated': True, 'authority_checked': 'current-effective-authority',
                'status_code': reply[0], 'positive_status_code': positive[0],
                'credential_tenant': tenant, 'requested_tenant': foreign if kind == 'cross-tenant' else tenant,
                'unauthorized_disclosure': False, 'unauthorized_mutation': False,
                'request_valid': True, 'response_valid': True,
                'state_before_sha256': hashlib.sha256(json.dumps(before).encode()).hexdigest(),
                'state_after_sha256': hashlib.sha256(json.dumps(after).encode()).hexdigest(),
                'revision': os.environ['GITHUB_SHA'], 'run_id': os.environ['GITHUB_RUN_ID'],
                'run_attempt': os.environ['GITHUB_RUN_ATTEMPT']})
    (c['out']/'planning-security-conformance.json').write_text(json.dumps(rows, indent=2)+'\n')
