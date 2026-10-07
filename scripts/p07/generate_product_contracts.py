"""Generate additive P07 proposal and job interfaces; existing v1 grants stay unchanged."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
UUID = {'type': 'string', 'format': 'uuid'}
SHA = {'type': 'string', 'pattern': '^[a-f0-9]{64}$'}


def obj(properties):
    return {'type': 'object', 'additionalProperties': False,
            'required': list(properties), 'properties': properties}


def param(name, location='path', schema=UUID):
    return {'name': name, 'in': location, 'required': True, 'schema': schema}


def operation(name, parameters, request=None, status='200'):
    result = {'operationId': name, 'parameters': parameters,
              'responses': {status: {'description': 'Current tenant-scoped result; Cache-Control: no-store, private.'},
                            **{str(s): {'description': 'Denied or held; no native write permission.'}
                               for s in (400, 401, 403, 404, 409, 413, 415, 422, 423, 503)}}}
    if request:
        result['requestBody'] = {'required': True, 'content': {'application/json': {
            'schema': {'$ref': '#/components/schemas/' + request}}}}
    return result


def spec(title, paths, schemas):
    return {'openapi': '3.1.0', 'info': {'title': title, 'version': '1.0.0',
            'description': 'Protected internal interface. Maximum request 4096 bytes. Workload and delegated actor authority are independently current. Plans and responses never grant provider write authority.'},
            'security': [{'Workload': []}], 'paths': paths,
            'components': {'securitySchemes': {'Workload': {'type': 'http', 'scheme': 'bearer'}},
                           'schemas': schemas}}


actor = param('X-Actor-Delegation', 'header', {'type': 'string', 'minLength': 1})
key = param('Idempotency-Key', 'header')
plan_path = '/v1/tenants/{tenant}/applications/{application}/environments/{environment}/native-plans'
plans = spec('Planning immutable native provisioning and retirement', {
    plan_path: {'post': operation('createNativePlan', [param(p) for p in ('tenant', 'application', 'environment')] + [actor, key], 'NativeProposal', '201')}},
    {'NativeProposal': obj({k: UUID for k in ('site_id', 'base_plan_id', 'recipe_id')})})
job_path = '/v1/tenants/{tenant}/native-jobs'
jobs = spec('Lifecycle native provisioning and retirement jobs', {
    job_path: {'post': operation('admitNativeJob', [param('tenant'), actor, key], 'PlanReference', '202')},
    job_path + '/{job}': {'get': operation('readNativeJob', [param('tenant'), param('job'), actor])},
    job_path + '/{job}/stop': {'post': operation('stopNativeJob', [param('tenant'), param('job'), actor], 'Stop', '202')}},
    {'PlanReference': obj({'plan_id': UUID, 'plan_revision': {'type': 'integer', 'minimum': 1},
                           'plan_digest': SHA, 'approval_id': UUID}),
     'Stop': obj({'expected_revision': {'type': 'integer', 'minimum': 1}})})
for name, value in (('planning-native-v1.json', plans), ('lifecycle-native-jobs-v1.json', jobs)):
    (ROOT / 'contracts/openapi' / name).write_text(json.dumps(value, indent=2) + '\n')
