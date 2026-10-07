"""Exercise the real Planning compiler against the real native Lifecycle resolver.

All owner replies here are explicitly synthetic. No platform effect is authorized.
"""
import sys
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

for method in DELTA:
    for mode in ('rehearsal', 'cutover', 'rollback', 'forward_recovery', 'reverse_recovery', 'cleanup'):
        base, bound, recipe = values(mode, method)
        actor, requester, approver = (str(uuid4()) for _ in range(3))
        base['executor_ids'] = [actor]
        recipe['base_content_sha256'] = digest(base)
        content = compose_migration(base, bound, recipe, 1000)
        content['native_migration'].update(recipe_id=str(uuid4()), base_plan_id=str(uuid4()))
        binding = bind(content, str(uuid4()), requester)
        record = {'content':content, 'binding':binding, 'invalidated':False}
        assignment = {'tenant_id':binding['tenant_id'], 'plan_id':binding['plan_id'],
                      'plan_revision':1, 'plan_digest':binding['digest'], 'actor_id':actor,
                      **{k:str(uuid4()) for k in ('approval_id','executor_id','campaign_id','epoch')}}
        config = Mock()
        config.load.return_value = {'expires_at':2000}
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
        transport.request.side_effect = [record, approval]
        resolved = NativeOwners(config, transport, lambda:1000).resolve(binding['tenant_id'], assignment)
        validate_plan(resolved, 1000)
        assert resolved['migration'] == content['native_migration']['migration']
        assert resolved['intents'] == content['native_migration']['intents']
        assert resolved['operation_plan_sha256'] == digest(content['native_migration'])
        assert resolved['expires_at'] == content['valid_until']
print('Thirty real Planning compiler -> native resolver combinations passed with synthetic owner consent; no native writes.')
