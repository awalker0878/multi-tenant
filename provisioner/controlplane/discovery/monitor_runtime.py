"""Installed unattended monitoring under current OIDC/IAM and evidence custody.

This service composes existing freshness checks and the alert-delivery owner.
It never uses a human access token, collection credentials, worker grants, a
native mutation route or a signing fallback. Credential rotation is supplied by
the commissioned identity agent; every operation rereads the protected token.
"""
import argparse
from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import signal
from threading import Event
from typing import Mapping

import psycopg
from psycopg.conninfo import conninfo_to_dict

from provisioner.controlplane.authority.directory import PostgresRoleDirectory
from provisioner.controlplane.authority.model import PlanScope
from provisioner.controlplane.authority.oidc import OIDCIdentityProvider
from provisioner.controlplane.authority.service import DISCOVERY_MONITOR, require_scoped_role
from provisioner.controlplane.evidence.runtime import EvidenceRuntimeConfig, build_gate
from provisioner.controlplane.persistence.environments import EnvironmentRepository
from provisioner.controlplane.persistence.store import AuditContext, TenantContext
from .alert_delivery import AlertDeliveryRepository
from .alert_transport import AlertOwnerTarget, HttpsAlertOwner
from .collector_settings import protected_path
from .freshness import FreshnessPolicy
from .freshness_history import FreshnessHistoryRepository
from .freshness_monitor import FreshnessMonitor, FreshnessMonitorPolicy, FreshnessMonitorTarget, _slot
from .model import _id, _scope, _utc
from .native_credentials import decode_json, read_protected
from .persistence import DiscoveryRepository
from .trust import _keys

_INSERT_TABLES=('discovery_freshness_checks','discovery_alert_deliveries','audit_events')
_SELECT_TABLES=(*_INSERT_TABLES,'discovery_generations','environment_registrations','evidence_entries',
               'audit_streams','evidence_streams')


@dataclass(frozen=True,slots=True)
class MonitorSettings:
    config_path:Path
    config_digest:str
    subject:str
    ctx:TenantContext
    token_file:Path=field(repr=False)
    targets:tuple[FreshnessMonitorTarget,...]
    policy:FreshnessMonitorPolicy
    freshness_policy:FreshnessPolicy
    owner:AlertOwnerTarget

    @classmethod
    def from_file(cls,path):
        path=protected_path(str(path));raw=read_protected(path,131072)
        doc=_keys(decode_json(raw,131072),{'format','subject','organizationId','tenantId',
                     'tokenFile','targets','policy','freshnessPolicy','alertOwner'})
        if (doc['format']!='hosting-discovery-monitor/1' or not _id(doc['subject'])
                or not _id(doc['organizationId']) or not _id(doc['tenantId'])):
            raise ValueError('Exact monitor service identity is required')
        ctx=TenantContext(doc['organizationId'],doc['tenantId'])
        policy=_keys(doc['policy'],{'intervalSeconds','maxTargets','maxCycles'})
        policy=FreshnessMonitorPolicy(policy['intervalSeconds'],policy['maxTargets'],policy['maxCycles'])
        freshness=_keys(doc['freshnessPolicy'],{'refreshAfterSeconds','maxAgeSeconds'})
        freshness=FreshnessPolicy(freshness['refreshAfterSeconds'],freshness['maxAgeSeconds'])
        if not isinstance(doc['targets'],list):raise ValueError('A bounded monitor target list is required')
        targets=[]
        for selected in doc['targets']:
            value=_keys(selected,{'environmentId','scope'})
            scope_doc=_keys(value['scope'],{'organizationId','tenantId','locationId',
                'securityDomainId','endpointId','nativeScopeId','platformFamily'})
            scope=PlanScope.from_record(scope_doc)
            if not _scope(scope) or (scope.organization_id,scope.tenant_id)!=(ctx.organization_id,ctx.tenant_id):
                raise ValueError('Monitor target is outside its configured service tenant')
            targets.append(FreshnessMonitorTarget(value['environmentId'],scope))
        targets=FreshnessMonitor._targets(targets,policy.max_targets)
        if len({target.scope for target in targets})!=len(targets):
            raise ValueError('Each monitor environment requires an unambiguous native scope')
        return cls(path,hashlib.sha256(raw).hexdigest(),doc['subject'],ctx,
                   protected_path(doc['tokenFile']),targets,policy,freshness,AlertOwnerTarget.parse(doc['alertOwner']))

    def recheck(self):
        if hashlib.sha256(read_protected(self.config_path,131072)).hexdigest()!=self.config_digest:
            raise PermissionError('Monitor deployment configuration changed; restart required')


def require_monitor_role(connect,role_name):
    """The monitor SQL login has only metadata reads and monitoring/audit appends."""
    if not isinstance(role_name,str) or re.fullmatch('[a-z][a-z0-9_]{0,62}',role_name) is None:
        raise ValueError('Exact dedicated monitor SQL login is required')
    with connect() as con:
        if con.autocommit:raise RuntimeError('Monitor access requires transactions')
        row=con.execute('SELECT current_user,rolsuper,rolbypassrls FROM pg_catalog.pg_roles WHERE rolname=current_user').fetchone()
        if row!=(role_name,False,False) or con.execute('SELECT hosting_controlplane.is_site_worker_role()').fetchone()!=(False,):
            raise RuntimeError('Monitor SQL role is not a dedicated RLS reader/appender')
        forbidden=con.execute("SELECT coalesce(bool_or(has_table_privilege(current_user,c.oid,'UPDATE') OR "
            "has_table_privilege(current_user,c.oid,'DELETE') OR has_table_privilege(current_user,c.oid,'TRUNCATE') OR "
            "has_table_privilege(current_user,c.oid,'TRIGGER') OR has_table_privilege(current_user,c.oid,'REFERENCES') OR "
            "(has_table_privilege(current_user,c.oid,'INSERT') AND NOT "
            "(n.nspname='hosting_controlplane' AND c.relname=ANY(%s))) OR "
            "(has_table_privilege(current_user,c.oid,'SELECT') AND NOT "
            "(n.nspname='hosting_controlplane' AND c.relname=ANY(%s)))),false) "
            "FROM pg_catalog.pg_class c JOIN pg_catalog.pg_namespace n ON n.oid=c.relnamespace "
            "WHERE c.relkind IN ('r','p') AND n.nspname NOT LIKE 'pg_%' AND n.nspname<>'information_schema'",
            (list(_INSERT_TABLES),list(_SELECT_TABLES))).fetchone()
        if forbidden!=(False,):raise RuntimeError('Monitor SQL login has unrelated mutation privileges')
        required=con.execute("SELECT bool_and(coalesce(has_table_privilege(current_user,to_regclass('hosting_controlplane.'||t.name),'SELECT'),false)) "
                             'FROM unnest(%s::text[]) AS t(name)',(list(_SELECT_TABLES),)).fetchone()
        writes=con.execute("SELECT bool_and(coalesce(has_table_privilege(current_user,to_regclass('hosting_controlplane.'||t.name),'INSERT'),false)) "
                           'FROM unnest(%s::text[]) AS t(name)',(list(_INSERT_TABLES),)).fetchone()
        rls=con.execute("SELECT count(*)=%s AND coalesce(bool_and(c.relrowsecurity AND c.relforcerowsecurity),false) "
            "FROM pg_catalog.pg_class c JOIN pg_catalog.pg_namespace n ON n.oid=c.relnamespace "
            "WHERE n.nspname='hosting_controlplane' AND c.relname=ANY(%s)",
            (len(_SELECT_TABLES),list(_SELECT_TABLES))).fetchone()
        if required!=(True,) or writes!=(True,) or rls!=(True,):
            raise RuntimeError('Monitor metadata/custody tables or forced RLS are unavailable')


class MonitorRuntime:
    def __init__(self,settings,*,identities,environments,history,delivery,evidence_gate,
                 clock=lambda:datetime.now(timezone.utc)):
        if not isinstance(settings,MonitorSettings):raise TypeError('Validated monitor settings are required')
        self.settings=settings;self.identities=identities;self.environments=environments
        self.history=history;self.delivery=delivery;self.evidence_gate=evidence_gate;self.clock=clock
        self.owner=HttpsAlertOwner(settings.owner)
        self.stopped=Event()
        self.monitor=FreshnessMonitor(history,policy=settings.policy,clock=clock)
        self._targets={target.scope:target for target in settings.targets}

    def authorize(self,scope,checked_at):
        if self.stopped.is_set():raise PermissionError('Monitoring service stopped')
        self.settings.recheck()
        if scope not in self._targets or not _utc(checked_at):raise PermissionError('Unenrolled monitoring scope')
        token=read_protected(self.settings.token_file,16384).decode('ascii').strip()
        principal=self.identities.authenticate(token)
        ctx=self.settings.ctx;at=self.clock()
        if (not _utc(at) or at<checked_at or (principal.subject,principal.kind,principal.organization_id,principal.tenant_id)
                !=(self.settings.subject,'SERVICE',ctx.organization_id,ctx.tenant_id)):
            raise PermissionError('Current enrolled monitoring service identity is unavailable')
        require_scoped_role(principal,DISCOVERY_MONITOR,scope,at)
        row=self.environments.get(ctx,self._targets[scope].environment_id)
        if row is None or row.scope!=scope:raise PermissionError('Registered monitoring target changed')
        self.evidence_gate.require(ctx)

    def cycle(self,*,retry_unknown=False,refresh=False):
        at=self.monitor._now()
        value=self.monitor.run_cycle(self.settings.ctx,self.settings.targets,actor_id=self.settings.subject,
                                     scheduled_at=at,authorize=self.authorize)
        items=[]
        for item in value['items']:
            target=next(target for target in self.settings.targets if target.environment_id==item['environmentId'])
            if item['status']!='CHECK_RETAINED' or item['alert'] is None:
                items.append({**item,'delivery':None});continue
            try:
                result=self.delivery.dispatch(self.settings.ctx,target.scope,target.environment_id,item['checkId'],
                    owner=self.owner,audit=AuditContext(self.settings.subject,item['checkId']),
                    authorize=self.authorize,retry_unknown=retry_unknown,refresh=refresh)
            except Exception:
                result={'status':'DELIVERY_HELD','notificationAttempted':None,
                        'reconciliationRequired':True,'executionAuthorized':False}
            items.append({**item,'notificationAttempted':result['notificationAttempted'],'delivery':result})
        held=any(item['status']=='CHECK_HELD' or item['delivery'] is not None
                 and item['delivery']['status'] in ('DELIVERY_HELD','DELIVERY_UNKNOWN') for item in items)
        return {'format':'hosting-discovery-monitor-service-cycle/1','status':'MONITOR_HELD' if held else 'MONITOR_EVALUATED',
            'scheduledAt':at.isoformat(),'slot':value['slot'],'items':items,
            'notificationDelivery':'CONFIGURED_AUTHENTICATED_OWNER','collectionRequested':False,'executionAuthorized':False}

    def reconcile(self,environment_id,check_id,*,retry_unknown=False,refresh=False):
        """Revisit an exact retained check, without creating a new monitoring slot."""
        if not _id(environment_id) or not _id(check_id):raise ValueError('Exact retained check selection is required')
        targets=[target for target in self.settings.targets if target.environment_id==environment_id]
        if len(targets)!=1:raise PermissionError('Environment is not enrolled for this monitor')
        target=targets[0]
        self.authorize(target.scope,self.clock())
        return self.delivery.dispatch(self.settings.ctx,target.scope,environment_id,check_id,
            owner=self.owner,audit=AuditContext(self.settings.subject,check_id),
            authorize=self.authorize,retry_unknown=retry_unknown,refresh=refresh)


def _required(values,name):
    value=values.get(name)
    if not isinstance(value,str) or not value or value!=value.strip():raise ValueError('Required monitor runtime setting is missing')
    return value


def _secure_dsn(value):
    options=conninfo_to_dict(value)
    if (options.get('sslmode')!='verify-full' or not options.get('host') or options['host'].startswith('/')
            or ',' in options['host'] or options.get('connect_timeout') not in (None,'5')):
        raise ValueError('Monitor database needs one verified TLS host and bounded timeout')
    return value


def create_runtime(settings,values:Mapping[str,str],*,connect_factory=None,evidence_gate=None,identities=None):
    dsn=_secure_dsn(_required(values,'HOSTING_MONITOR_DSN'))
    directory_dsn=_secure_dsn(_required(values,'HOSTING_DIRECTORY_DSN'))
    if dsn==directory_dsn:raise ValueError('Monitor and directory database credentials must be distinct')
    connect=lambda:psycopg.connect(dsn,connect_timeout=5,autocommit=False)
    directory_connect=lambda:psycopg.connect(directory_dsn,connect_timeout=5,autocommit=False)
    if connect_factory is not None:connect,directory_connect=connect_factory
    monitor_role=_required(values,'HOSTING_MONITOR_DB_ROLE')
    require_monitor_role(connect,monitor_role)
    with directory_connect() as con:
        role=con.execute('SELECT current_user,rolsuper,rolbypassrls FROM pg_catalog.pg_roles WHERE rolname=current_user').fetchone()
        if role is None or role[0]==monitor_role or role[1:]!=(False,False):
            raise RuntimeError('Monitor and directory SQL logins must be distinct RLS roles')
    if identities is None:
        identities=OIDCIdentityProvider(issuer=_required(values,'HOSTING_OIDC_ISSUER'),
            audience=_required(values,'HOSTING_OIDC_AUDIENCE'),jwks_uri=_required(values,'HOSTING_OIDC_JWKS_URI'),
            directory=PostgresRoleDirectory(directory_connect),step_up_acr=frozenset({'monitor-service-unused-step-up'}))
    history=FreshnessHistoryRepository(DiscoveryRepository(connect),policy=settings.freshness_policy)
    if evidence_gate is None:
        # The verification role is this same metadata reader; it holds no signing credential.
        evidence_values=dict(values);evidence_values['HOSTING_RUNTIME_DSN']=dsn
        config=EvidenceRuntimeConfig.from_environment(evidence_values,require_scopes=True)
        if settings.ctx not in config.startup_scopes():
            raise ValueError('Monitor tenant is absent from commissioned evidence custody')
        evidence_gate=build_gate(config,connection_factory=connect)
    result=MonitorRuntime(settings,identities=identities,environments=EnvironmentRepository(connect),
        history=history,delivery=AlertDeliveryRepository(history),evidence_gate=evidence_gate)
    for target in settings.targets:result.authorize(target.scope,result.clock())
    return result


class _Parser(argparse.ArgumentParser):
    def error(self,message):raise ValueError('Invalid monitoring command arguments')


def main(argv=None):
    parser=_Parser(description=__doc__,allow_abbrev=False)
    parser.add_argument('action',choices=('cycle','run','retry-unknown','refresh-acknowledgements'))
    parser.add_argument('--config',required=True)
    parser.add_argument('--duration-seconds',type=int,default=3600)
    parser.add_argument('--environment-id')
    parser.add_argument('--check-id')
    try:
        args=parser.parse_args(argv)
        if not 1<=args.duration_seconds<=604800:raise ValueError('Bounded runtime is required')
        settings=MonitorSettings.from_file(args.config);runtime=create_runtime(settings,os.environ)
        if args.action in ('retry-unknown','refresh-acknowledgements'):
            if args.environment_id is None or args.check_id is None:
                raise ValueError('An exact retained environment/check is required for reconciliation')
            result=runtime.reconcile(args.environment_id,args.check_id,retry_unknown=args.action=='retry-unknown',
                                     refresh=args.action=='refresh-acknowledgements')
            print(json.dumps(result,sort_keys=True))
            return 3 if result['status']=='DELIVERY_UNKNOWN' else 0
        if args.environment_id is not None or args.check_id is not None:
            raise ValueError('Retained-check selectors are only accepted for reconciliation')
        stopped=runtime.stopped
        for name in ('SIGINT','SIGTERM'):
            if hasattr(signal,name):signal.signal(getattr(signal,name),lambda *_:stopped.set())
        started=runtime.monitor._now();deadline=started.timestamp()+args.duration_seconds
        count=0;prior=None;code=0
        while count<settings.policy.max_cycles and not stopped.is_set():
            at=runtime.monitor._now()
            if at.timestamp()>=deadline:break
            slot=_slot(at,settings.policy.interval_seconds)
            if slot!=prior:
                result=runtime.cycle(retry_unknown=args.action=='retry-unknown',
                                     refresh=args.action=='refresh-acknowledgements')
                print(json.dumps(result,sort_keys=True),flush=True)
                code=max(code,0 if result['status']=='MONITOR_EVALUATED' else 2);count+=1;prior=slot
            if args.action!='run':break
            stopped.wait(min(30,max(0,min(deadline,(slot+1)*settings.policy.interval_seconds)-runtime.monitor._now().timestamp())))
        return code
    except KeyboardInterrupt:return 130
    except Exception:
        print(json.dumps({'format':'hosting-discovery-monitor-service-cycle/1','status':'MONITOR_HELD',
                         'collectionRequested':False,'executionAuthorized':False},sort_keys=True))
        return 2


if __name__=='__main__':raise SystemExit(main())
