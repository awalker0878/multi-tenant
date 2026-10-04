"""PostgreSQL admission for cooperating enrolled discovery hosts.

Existing signed campaign/native-credential owners authorize every native GET.
This owner only reduces admission. Durable starts consume all five fleet limit
dimensions until the existing transport actually closes its local socket. Lost
DB receipts, process death and elapsed deadlines never imply capacity is free.
"""
from contextlib import contextmanager
import argparse
from dataclasses import dataclass,field
from datetime import datetime,timezone,timedelta
import hashlib
import ipaddress
import json
import math
import os
from pathlib import Path
import re
import sys
import time
from uuid import uuid4

import psycopg
from psycopg.conninfo import conninfo_to_dict
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from .collector_settings import protected_path
from .model import DiscoveryCampaignAuthorization,_id,_json,_utc
from .native_credentials import decode_json,read_protected
from .read_budget import NativeReadAdmissionHeld,NativeReadGate
from .review_files import publish_once
from .service_enrollment import ServiceEnrollment,capture_service_facts
from .trust import _decode,_keys

_SHA=re.compile('[0-9a-f]{64}')


def bucket_ids(scope):
    parts=[['TOTAL'],['ORGANIZATION',scope.organization_id],
           ['TENANT',scope.organization_id,scope.tenant_id],
           ['WSD',scope.organization_id,scope.tenant_id,scope.site_id,scope.security_domain_id],
           ['ENDPOINT',scope.organization_id,scope.site_id,scope.platform_family,scope.endpoint_id]]
    # PostgreSQL jsonb_build_array::text uses the same space-separated JSON for
    # these ASCII IDs. Native scope is deliberately outside the endpoint bucket.
    return tuple(hashlib.sha256(json.dumps(value).encode('ascii')).hexdigest() for value in parts)


@dataclass(frozen=True,slots=True)
class FleetBudgetSettings:
    path:Path
    digest:str
    fleet_id:str
    worker_id:str
    role:str
    policy_digest:str
    database_ca_digest:str
    dsn_file:Path=field(repr=False)
    enrollment:ServiceEnrollment

    @classmethod
    def from_file(cls,path):
        path=protected_path(str(path));raw=read_protected(path,65536)
        doc=_keys(decode_json(raw,65536),{'format','fleetId','workerId','databaseRole','policyDigest','databaseCaDigest',
                                       'dsnFile','serviceEnrollmentFile','serviceEnrollmentDigest'})
        if (doc['format']!='hosting-discovery-fleet-budget/1'
                or not all(_id(doc[key]) for key in ('fleetId','workerId'))
                or not isinstance(doc['databaseRole'],str) or re.fullmatch('[a-z][a-z0-9_]{0,62}',doc['databaseRole']) is None
                or any(not isinstance(doc[name],str) or _SHA.fullmatch(doc[name]) is None
                       for name in ('policyDigest','databaseCaDigest'))):
            raise ValueError('An exact enrolled PostgreSQL fleet owner is required')
        return cls(path,hashlib.sha256(raw).hexdigest(),doc['fleetId'],doc['workerId'],doc['databaseRole'],
                   doc['policyDigest'],doc['databaseCaDigest'],protected_path(doc['dsnFile']),
                   ServiceEnrollment.from_file(doc['serviceEnrollmentFile'],doc['serviceEnrollmentDigest']))

    def recheck(self):
        if hashlib.sha256(read_protected(self.path,65536)).hexdigest()!=self.digest:
            raise PermissionError('Fleet configuration changed; restart required')
        self.enrollment.require_current()

    def connect(self):
        self.recheck()
        return _database_connect(self.dsn_file,self.role,self.database_ca_digest)


def _database_connect(dsn_file,role,ca_digest):
        dsn=read_protected(dsn_file,16384).decode('utf-8').strip()
        options=conninfo_to_dict(dsn)
        allowed={'host','hostaddr','port','dbname','user','password','sslmode','sslrootcert','connect_timeout'}
        if (options.get('user')!=role or options.get('sslmode')!='verify-full'
                or not options.get('host') or options['host'].startswith('/') or ',' in options['host']
                or not options.get('hostaddr') or not options.get('dbname') or not options.get('password')
                or not options.get('sslrootcert') or not options.get('port')
                or options.get('connect_timeout') not in (None,'1')
                or not set(options)<=allowed or any(key.startswith('PG') for key in os.environ)
                or os.environ.get('SSLKEYLOGFILE')):
            raise NativeReadAdmissionHeld('Fleet database needs one protected verified TLS login')
        address=ipaddress.ip_address(options['hostaddr'])
        if str(address)!=options['hostaddr'] or address.is_unspecified or address.is_multicast:
            raise NativeReadAdmissionHeld('Fleet database address is not pinned')
        ca=read_protected(protected_path(options['sslrootcert']),1024*1024,secret=False)
        if hashlib.sha256(ca).hexdigest()!=ca_digest:
            raise NativeReadAdmissionHeld('Fleet database trust bundle changed')
        # No injected DSN options can override transaction/lock bounds. Every
        # connection attempt also consumes the caller's original read deadline.
        return psycopg.connect(dsn,connect_timeout=1,autocommit=False,passfile='/dev/null',
                               sslcertmode='disable',gssencmode='disable',require_auth='scram-sha-256',
                               channel_binding='require',ssl_min_protocol_version='TLSv1.2',
                               options='-c statement_timeout=500 -c lock_timeout=100')


class PostgresFleetBudget:
    def __init__(self,settings:FleetBudgetSettings,*,connect=None):
        if not isinstance(settings,FleetBudgetSettings):raise TypeError('Enrolled fleet settings are required')
        self.settings=settings;self.connect=settings.connect if connect is None else connect
        if not callable(self.connect):raise TypeError('Fleet PostgreSQL connector is required')
        self.instance_id=uuid4().hex
        self.require_role()
        self.inspect()

    def require_role(self):
        _require_isolated_role(self.connect,self.settings.role,(True,True,True,False))

    def inspect(self):
        self.settings.recheck()
        with self.connect() as con:
            doc=con.execute('SELECT hosting_controlplane.discovery_fleet_inspect(%s,%s,%s)',
                (self.settings.fleet_id,self.settings.worker_id,self.settings.enrollment.digest)).fetchone()[0]
        if not isinstance(doc,dict) or doc.get('policyDigest')!=self.settings.policy_digest or doc.get('enabled') is not True:
            raise NativeReadAdmissionHeld('Fleet policy differs from the commissioned owner')
        return doc

    def admit(self,campaign,environment_id,deadline):
        self.settings.recheck()
        remaining=deadline-time.monotonic()
        if remaining<=0:raise NativeReadAdmissionHeld('Fleet admission consumed the native read deadline')
        now=datetime.now(timezone.utc)
        expires=min(now+timedelta(seconds=min(remaining,14.5)),campaign.expires_at)
        scope=campaign.scope
        doc={'format':'hosting-discovery-fleet-read/1','leaseId':uuid4().hex,'instanceId':self.instance_id,
             'organizationId':scope.organization_id,'tenantId':scope.tenant_id,'siteId':scope.site_id,
             'securityDomainId':scope.security_domain_id,'endpointId':scope.endpoint_id,
             'nativeScopeId':scope.native_scope_id,'platformFamily':scope.platform_family,
             'environmentId':environment_id,'collectorId':campaign.collector_id,
             'campaignDigest':campaign.digest(),'expiresAt':expires.isoformat()}
        raw=_json(doc);digest=hashlib.sha256(raw.encode('ascii')).hexdigest()
        # A failed execute/commit is an unknown admission, not THROTTLED. Never
        # issue another lease after losing the original receipt.
        with self.connect() as con:
            row=con.execute('SELECT * FROM hosting_controlplane.discovery_fleet_admit(%s,%s,%s,%s,%s)',
                (self.settings.fleet_id,self.settings.worker_id,self.settings.enrollment.digest,raw,digest)).fetchone()
        if row is None or row[0] not in ('THROTTLED','LEASE_STARTED'):
            raise NativeReadAdmissionHeld('Original fleet admission outcome is unknown')
        if row[0]=='THROTTLED':return None
        if row[1]!=doc['leaseId'] or not _utc(row[2]) or not _utc(row[3]) or not row[2]<row[3]<=expires:
            raise NativeReadAdmissionHeld('Original fleet receipt differs from the bounded request')
        return doc['leaseId'],digest

    def observed_close(self,lease):
        self.settings.recheck()
        with self.connect() as con:
            row=con.execute('SELECT hosting_controlplane.discovery_fleet_close(%s,%s,%s,%s,%s,%s)',
                (self.settings.fleet_id,self.settings.worker_id,self.settings.enrollment.digest,
                 self.instance_id,*lease)).fetchone()
        if row not in (('LOCAL_SOCKET_CLOSED',),('ALREADY_CLOSED',)):
            raise NativeReadAdmissionHeld('Original fleet socket-close receipt is unknown')


def _require_isolated_role(connect,role,permissions):
        with connect() as con:
            if con.autocommit:raise NativeReadAdmissionHeld('Fleet coordinator needs explicit transactions')
            if con.execute('SELECT session_user,current_user,rolsuper,rolbypassrls,rolcreaterole,rolcreatedb,rolreplication FROM pg_catalog.pg_roles WHERE rolname=current_user').fetchone()!=(role,role,False,False,False,False,False):
                raise NativeReadAdmissionHeld('Fleet login is not the enrolled isolated SQL role')
            if con.execute('SELECT hosting_controlplane.is_site_worker_role()').fetchone()!=(False,):
                raise NativeReadAdmissionHeld('Native mutation workers cannot operate the fleet budget')
            if con.execute('SELECT coalesce(bool_or(pg_has_role(session_user,r.oid,%s)),false) FROM pg_catalog.pg_roles r WHERE r.rolname<>session_user',('member',)).fetchone()!=(False,):
                raise NativeReadAdmissionHeld('Fleet login has another SQL role membership')
            if con.execute("SELECT has_database_privilege(current_user,current_database(),'CREATE'),coalesce(bool_or(has_schema_privilege(current_user,n.oid,'CREATE')),false) FROM pg_catalog.pg_namespace n WHERE left(n.nspname,3)<>'pg_' AND n.nspname<>'information_schema'").fetchone()!=(False,False):
                raise NativeReadAdmissionHeld('Fleet login can create database objects')
            forbidden=con.execute("SELECT coalesce(bool_or(has_table_privilege(current_user,c.oid,'SELECT,INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER')),false) FROM pg_catalog.pg_class c JOIN pg_catalog.pg_namespace n ON n.oid=c.relnamespace WHERE c.relkind IN ('r','p') AND n.nspname NOT LIKE %s AND n.nspname<>'information_schema'",('pg_%',)).fetchone()
            if forbidden!=(False,):raise NativeReadAdmissionHeld('Fleet login has direct data privileges')
            columns=con.execute("SELECT coalesce(bool_or(has_column_privilege(current_user,c.oid,a.attnum,'SELECT,INSERT,UPDATE,REFERENCES')),false) FROM pg_catalog.pg_class c JOIN pg_catalog.pg_namespace n ON n.oid=c.relnamespace JOIN pg_catalog.pg_attribute a ON a.attrelid=c.oid WHERE c.relkind IN ('r','p') AND a.attnum>0 AND NOT a.attisdropped AND n.nspname NOT LIKE %s AND n.nspname<>'information_schema'",('pg_%',)).fetchone()
            if columns!=(False,):raise NativeReadAdmissionHeld('Fleet login has direct column privileges')
            probes=con.execute("SELECT has_function_privilege(current_user,'hosting_controlplane.discovery_fleet_admit(text,text,text,text,text)','EXECUTE'),has_function_privilege(current_user,'hosting_controlplane.discovery_fleet_close(text,text,text,text,text,text)','EXECUTE'),has_function_privilege(current_user,'hosting_controlplane.discovery_fleet_inspect(text,text,text)','EXECUTE'),has_function_privilege(current_user,'hosting_controlplane.discovery_fleet_fenced_close(text,text,text,text)','EXECUTE')").fetchone()
            if probes!=permissions:raise NativeReadAdmissionHeld('Fleet login lacks its isolated owner capabilities')


class FleetNativeReadGate(NativeReadGate):
    def __init__(self,policy,*,budget:PostgresFleetBudget,stopped=None):
        super().__init__(policy,stopped=stopped)
        if not isinstance(budget,PostgresFleetBudget):raise TypeError('The existing PostgreSQL fleet owner is required')
        self.budget=budget

    def bind_campaign(self,campaign,environment_id):
        self.require_scope(campaign.scope)
        if not isinstance(campaign,DiscoveryCampaignAuthorization) or not _id(environment_id):
            raise NativeReadAdmissionHeld('Exact signed collection campaign is required')
        return BoundFleetNativeReadGate(self.policy,budget=self.budget,stopped=self._stopped,
                                       campaign=campaign,environment_id=environment_id,local_gate=self)

    @contextmanager
    def permit(self,deadline,authorize):
        raise NativeReadAdmissionHeld('Fleet read requires its exact verified campaign binding')
        yield


class BoundFleetNativeReadGate(FleetNativeReadGate):
    def __init__(self,policy,*,budget,stopped,campaign,environment_id,local_gate):
        super().__init__(policy,budget=budget,stopped=stopped)
        self.campaign=campaign;self.environment_id=environment_id
        self.local_gate=local_gate

    @contextmanager
    def permit(self,deadline,authorize):
        if type(deadline) not in (int,float) or not math.isfinite(deadline) or not callable(authorize):
            raise NativeReadAdmissionHeld('Current authority and bounded read deadline are required')
        # Keep the existing batch's additional process concurrency/rate ceiling.
        # The PostgreSQL owner then admits all global dimensions atomically.
        with NativeReadGate.permit(self.local_gate,deadline,authorize):
            lease=None
            while lease is None:
                self.check();authorize();self.check()
                lease=self.budget.admit(self.campaign,self.environment_id,deadline)
                if lease is None:
                    if time.monotonic()>=deadline:raise NativeReadAdmissionHeld('Fleet read admission deadline expired')
                    self._stopped.wait(min(.025,max(0,deadline-time.monotonic())))
            entered_native=False
            try:
                self.check();authorize();self.check()
                if time.monotonic()>=deadline:raise NativeReadAdmissionHeld('Fleet read deadline expired after admission')
                entered_native=True
                yield
            except BaseException:
                # Failed cleanup is not an observed close. A refusal before the
                # native owner enters the permit did not open a native socket.
                if not entered_native:self.budget.observed_close(lease)
                raise
            else:
                # native_https exits this context only after all socket/buffer
                # closes. SIGKILL/host death cannot run this or free the lease.
                self.budget.observed_close(lease)


@dataclass(frozen=True,slots=True)
class FleetFenceSettings:
    path:Path
    digest:str
    fleet_id:str
    role:str
    database_ca_digest:str
    dsn_file:Path=field(repr=False)
    public_key:bytes
    enrollment:ServiceEnrollment

    @classmethod
    def from_file(cls,path):
        path=protected_path(str(path));raw=read_protected(path,65536)
        doc=_keys(decode_json(raw,65536),{'format','fleetId','databaseRole','databaseCaDigest','dsnFile',
            'fencePublicKey','serviceEnrollmentFile','serviceEnrollmentDigest'})
        if (doc['format']!='hosting-discovery-fleet-fence-receiver/1' or not _id(doc['fleetId'])
                or not isinstance(doc['databaseRole'],str) or re.fullmatch('[a-z][a-z0-9_]{0,62}',doc['databaseRole']) is None
                or not isinstance(doc['databaseCaDigest'],str) or _SHA.fullmatch(doc['databaseCaDigest']) is None):
            raise ValueError('An independently enrolled fence receiver is required')
        return cls(path,hashlib.sha256(raw).hexdigest(),doc['fleetId'],doc['databaseRole'],
            doc['databaseCaDigest'],protected_path(doc['dsnFile']),_decode(doc['fencePublicKey'],32),
            ServiceEnrollment.from_file(doc['serviceEnrollmentFile'],doc['serviceEnrollmentDigest']))

    def recheck(self):
        if hashlib.sha256(read_protected(self.path,65536)).hexdigest()!=self.digest:
            raise PermissionError('Fleet fence configuration changed; restart required')
        self.enrollment.require_current()

    def connect(self):
        self.recheck()
        return _database_connect(self.dsn_file,self.role,self.database_ca_digest)


def reconcile_fenced_read(*,connect,fleet_id,receipt_path,public_key,service_digest,recheck):
    """Independent receiver: verify a current signed exact old-worker fence.

    The SQL login must be the separately commissioned fencer, never the collector.
    This verifies proof supplied by the actual host/network fence owner; it does
    not manufacture that proof or infer fence success from worker absence.
    """
    if (not _id(fleet_id) or not isinstance(public_key,bytes) or len(public_key)!=32
            or not isinstance(service_digest,str) or _SHA.fullmatch(service_digest) is None or not callable(recheck)):
        raise ValueError('An independently enrolled fence receiver is required')
    recheck()
    envelope=_keys(decode_json(read_protected(protected_path(str(receipt_path)),8192),8192),{'receipt','signature'})
    doc=_keys(envelope['receipt'],{'format','fleetId','leaseId','workerId','instanceId','serviceDigest',
        'requestDigest','observerId','observationId','observedAt','expiresAt','oldProcessExcluded','oldSocketsClosed'})
    now=datetime.now(timezone.utc)
    observed,expires=(datetime.fromisoformat(doc[name]) for name in ('observedAt','expiresAt'))
    if (doc['format']!='hosting-discovery-fleet-fence-receipt/1' or doc['fleetId']!=fleet_id
            or any(not _id(doc[name]) for name in ('workerId','observerId','observationId'))
            or any(not isinstance(doc[name],str) or re.fullmatch('[0-9a-f]{32}',doc[name]) is None for name in ('leaseId','instanceId'))
            or any(not isinstance(doc[name],str) or _SHA.fullmatch(doc[name]) is None for name in ('serviceDigest','requestDigest'))
            or not _utc(observed) or not _utc(expires) or not observed<=now<expires
            or now-observed>timedelta(minutes=5) or expires-observed>timedelta(minutes=15)
            or doc['oldProcessExcluded'] is not True or doc['oldSocketsClosed'] is not True):
        raise NativeReadAdmissionHeld('Independent fence receipt is stale or incomplete')
    Ed25519PublicKey.from_public_bytes(public_key).verify(_decode(envelope['signature'],64),_json(doc).encode('ascii'))
    recheck()
    with connect() as con:
        row=con.execute('SELECT hosting_controlplane.discovery_fleet_fenced_close(%s,%s,%s,%s)',
            (fleet_id,_json(envelope),hashlib.sha256(public_key).hexdigest(),service_digest)).fetchone()
    if row!=('INDEPENDENT_WORKER_FENCED',):raise NativeReadAdmissionHeld('Fence reconciliation is unconfirmed')
    return {'format':'hosting-discovery-fleet-reconciliation/1','status':row[0],'leaseId':doc['leaseId'],
            'observationId':doc['observationId'],'executionAuthorized':False}


def main(argv=None):
    parser=argparse.ArgumentParser(description='Installed discovery fleet owner commands')
    commands=parser.add_subparsers(dest='command',required=True)
    inspect=commands.add_parser('inspect',help='Read only this enrolled worker\'s original lease outcomes')
    inspect.add_argument('--config',required=True)
    facts=commands.add_parser('service-facts',help='Capture actual installed service facts for independent enrollment')
    facts.add_argument('--service-id',required=True);facts.add_argument('--store',action='append',required=True)
    facts.add_argument('--output',required=True)
    reconcile=commands.add_parser('reconcile-fenced',help='Receive an actual independent signed worker/socket fence')
    reconcile.add_argument('--config',required=True);reconcile.add_argument('--receipt',required=True)
    args=parser.parse_args(argv)
    try:
        if args.command=='inspect':
            settings=FleetBudgetSettings.from_file(args.config)
            result={'format':'hosting-discovery-fleet-inspection/1','fleetId':settings.fleet_id,
                'workerId':settings.worker_id,'executionAuthorized':False,
                **PostgresFleetBudget(settings).inspect()}
        elif args.command=='service-facts':
            stores={}
            for selected in args.store:
                name,separator,value=selected.partition('=')
                if not separator or not _id(name) or not value or name in stores:
                    raise ValueError('Each retained store needs one exact NAME=absolute-path selection')
                stores[name]=protected_path(value)
            document=capture_service_facts(args.service_id,stores);raw=_json(document).encode('ascii')
            output=protected_path(args.output)
            def current():
                if capture_service_facts(args.service_id,stores)!=document:
                    raise PermissionError('Actual service facts changed during capture')
            publish_once(str(output),raw,current)
            result={'format':'hosting-discovery-service-facts-capture/1','status':'FACTS_CAPTURED',
                'path':str(output),'digest':hashlib.sha256(raw).hexdigest(),
                'enrollmentIssued':False,'executionAuthorized':False}
        else:
            settings=FleetFenceSettings.from_file(args.config)
            _require_isolated_role(settings.connect,settings.role,(False,False,False,True))
            result=reconcile_fenced_read(connect=settings.connect,fleet_id=settings.fleet_id,
                receipt_path=args.receipt,public_key=settings.public_key,
                service_digest=settings.enrollment.digest,recheck=settings.recheck)
        print(_json(result));return 0
    except (Exception,KeyboardInterrupt):
        print(_json({'format':'hosting-discovery-fleet-command/1','status':'OWNER_HELD',
            'command':args.command,'executionAuthorized':False}),file=sys.stderr)
        return 2


if __name__=='__main__':raise SystemExit(main())
