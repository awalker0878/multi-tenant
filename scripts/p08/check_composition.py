"""Exercise the real Planning compiler against the real native Lifecycle resolver.

All owner replies here are explicitly synthetic. No platform effect is authorized.
"""
import sys
from copy import deepcopy
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from unittest.mock import Mock
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'services/planning/src'), str(ROOT / 'services/planning/tests'),
               str(ROOT / 'services/lifecycle/src')]
from test_migration_plans import values
from planning.domain.compilation import bind
from planning.domain.migration_plan import DELTA, compose_migration
from planning.domain.model import digest
from lifecycle.infrastructure.native_owners import NativeOwners
from lifecycle.domain.native_workflow import validate_plan
from lifecycle.domain.capability_definitions import METHOD_ALIASES
from lifecycle.domain.execution import Rejected

locator = spec_from_file_location('_composition_readiness', ROOT / 'services/lifecycle/tests/test_migration_readiness.py')
if locator is None or locator.loader is None:
    raise RuntimeError('Current Lifecycle readiness test specimen unavailable')
readiness_fixture = module_from_spec(locator)
locator.loader.exec_module(readiness_fixture)


def readiness(content, tenant):
    # Explicit synthetic E2 data: exercise every current resolver check. This
    # is neither enrollment nor E3/E4 evidence and cannot authorize an effect.
    value, _ = readiness_fixture.specimen()
    migration = content['native_migration']['migration']
    value.update(scope={'tenant_id': tenant, 'application_id': content['scope']['resource_id'],
                        'environment_id': content['scope']['environment'], 'site_id': content['scope']['site_id']},
                 route_sha256=content['migration_campaign']['route_sha256'],
                 method=METHOD_ALIASES[migration['method']], evaluated_at=1000, expires_at=1100)
    for side in ('source', 'target'):
        value[side].update(profile_sha256=migration[side]['profile_sha256'])
    recon = value['workload_reconciliation']
    recon.update(source_profile_sha256=migration['source']['profile_sha256'],
                 native_review_sha256=migration['review']['digest'], expires_at=1100)
    recon['reconciliation_sha256'] = digest({k:v for k,v in recon.items() if k != 'reconciliation_sha256'})
    for coverage in value['collection_coverages']:
        side = 'target' if coverage['scope'] == 'target' else 'source'
        coverage.update(platform=value[side]['platform'], installed_tuple_sha256=migration[side]['tuple_sha256'],
                        evaluated_at=1000, expires_at=1100)
        coverage['coverage_sha256'] = digest({k:v for k,v in coverage.items() if k != 'coverage_sha256'})
    value['readiness_sha256'] = digest({k:v for k,v in value.items() if k != 'readiness_sha256'})
    return value

for method in DELTA:
    for mode in ('rehearsal', 'cutover', 'rollback', 'forward_recovery', 'reverse_recovery', 'cleanup'):
        base, bound, recipe = values(mode, method)
        actor, requester, approver = (str(uuid4()) for _ in range(3))
        base['executor_ids'] = [actor]
        recipe['base_content_sha256'] = digest(base)
        content = compose_migration(base, bound, recipe, 1000)
        content['native_migration'].update(recipe_id=str(uuid4()), base_plan_id=str(uuid4()))
        binding = bind(content, str(uuid4()), requester)
        record = {'content':content, 'binding':binding, 'invalidated':False,
                  'migration_readiness':readiness(content, binding['tenant_id'])}
        assignment = {'tenant_id':binding['tenant_id'], 'plan_id':binding['plan_id'],
                      'plan_revision':1, 'plan_digest':binding['digest'], 'actor_id':actor,
                      **{k:str(uuid4()) for k in ('approval_id','executor_id','campaign_id','epoch')}}
        config = Mock()
        config.load.return_value = {'expires_at':2000, 'owners':{'catalogue':{}}}
        config.assignment.return_value = assignment
        approval = {'allowed':True, 'tenant_id':binding['tenant_id'], 'actor_id':actor,
                    'approval_id':assignment['approval_id'], 'plan_digest':binding['digest'],
                    'authority_use':'native_approval', 'native_write_authorized':False,
                    'evaluated_at':1000, 'executor_fingerprint':digest('synthetic executor'),
                    'requester_id':requester, 'approval':{'state':'approved','revoked':False,
                    'approver_grant_current':True, 'approver_id':approver, 'plan_id':binding['plan_id'],
                    'plan_revision':1, 'plan_digest':binding['digest'], 'expires_at':1500,
                    'scope':{k:binding[k] for k in ('site_id','environment','resource_id')}}}
        transport = Mock()
        recon = record['migration_readiness']['workload_reconciliation']
        published = {'revision_id':recon['catalogue_revision_id'], 'intent_sha256':recon['catalogue_sha256'],
                     'intent':{'environment':{'id':content['scope']['environment']},
                               'workloads':[{'id':w['workload_id']} for w in recon['workloads']]}}
        replies = {'planning':record, 'catalogue':published, 'governance':approval}
        transport.request.side_effect = lambda owner, *_: deepcopy(replies[owner])
        owners = NativeOwners(config, transport, lambda:1000)
        resolved = owners.resolve(binding['tenant_id'], assignment)
        validate_plan(resolved, 1000)
        assert resolved['migration'] == content['native_migration']['migration']
        assert resolved['intents'] == content['native_migration']['intents']
        assert resolved['operation_plan_sha256'] == digest(content['native_migration'])
        assert resolved['expires_at'] == content['valid_until']
        for fault in ('missing_readiness', 'catalogue_workload', 'stale_readiness'):
            altered = deepcopy(replies)
            if fault == 'missing_readiness':
                altered['planning'].pop('migration_readiness')
            elif fault == 'catalogue_workload':
                altered['catalogue']['intent']['workloads'].append({'id':str(uuid4())})
            else:
                altered['planning']['migration_readiness']['expires_at'] = 999
                receipt = altered['planning']['migration_readiness']
                receipt['readiness_sha256'] = digest({k:v for k,v in receipt.items() if k != 'readiness_sha256'})
            transport.request.side_effect = lambda owner, *_: deepcopy(altered[owner])
            try:
                owners.resolve(binding['tenant_id'], assignment)
            except Rejected:
                pass
            else:
                raise AssertionError(fault + ' accepted by current native resolver')
print('Thirty Planning compiler -> native resolver combinations and ninety denial controls passed with synthetic E2 owner replies; no native writes or E3/E4 qualification.')
