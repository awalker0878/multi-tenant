"""Bounded probes of real private dependencies. Only sanitized observations are emitted."""
from __future__ import annotations
import asyncio
import base64
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import socket
import ssl
import sys
import time

CHECKS = []
CA = '/run/secrets/ca.crt'
BUCKET = 'p01-evidence'
KEY = 't_demo/campaign/evidence.json'
PAYLOAD = b'{"scope":"synthetic","witness":"retained version one","native_writes":false}\n'


def secret(name):
    return (Path('/run/secrets')/name).read_text().strip()


def check(name, condition, observation=None):
    CHECKS.append({'name': name, 'passed': bool(condition), 'observation': observation})
    if not condition:
        raise AssertionError(name)


def denied(name, call, errors, codes=None, *, worm=False):
    try:
        call()
    except errors as error:
        code = getattr(error, 'reply_code', None)
        observation={'error_type':type(error).__name__,'code':code}
        if hasattr(error,'response'):
            code=error.response['Error']['Code']
            observation.update(code=code,message=error.response['Error'].get('Message'),http_status=error.response['ResponseMetadata']['HTTPStatusCode'])
        valid=codes is None or code in codes
        if worm:
            valid=valid and observation.get('http_status')==400 and observation.get('message','').startswith('Object is WORM protected and cannot be overwritten')
        check(name,valid,observation)
    else:
        check(name, False, 'unexpected authorization')


def closed_port(host, port):
    try:
        with socket.create_connection((host,port),timeout=2): pass
    except ConnectionRefusedError:
        check(f'{host}-{port}-not-client-accessible',True)
    else:
        check(f'{host}-{port}-not-client-accessible',False)


def broker_connect(identity, password=None, vhost='p01', tls=True):
    import pika
    password_file = identity+'-password' if identity != 'foreign' else 'foreign-broker-password'
    return pika.BlockingConnection(pika.ConnectionParameters('rabbit', 5671 if tls else 5672, vhost, pika.PlainCredentials(identity, password or secret(password_file)), ssl_options=pika.SSLOptions(ssl.create_default_context(cafile=CA), 'rabbit') if tls else None, connection_attempts=1, socket_timeout=3, stack_timeout=5, blocked_connection_timeout=3, heartbeat=10))


def broker(stage):
    import pika
    errors = pika.exceptions
    if stage == 'broker-outage':
        denied('broker-outage-is-visible', lambda: broker_connect('publisher'), (errors.AMQPConnectionError, OSError))
        return {}
    if stage == 'broker-revoked':
        denied('revoked-broker-user-denied', lambda: broker_connect('publisher'), errors.ProbableAuthenticationError)
        return {}
    if stage == 'broker-before':
        for port in (15672,15692): closed_port('rabbit',port)
        for identity, password, vhost, name in [('publisher','incorrect-synthetic-password','p01','invalid-broker-secret-denied'), ('foreign',None,'p01','foreign-vhost-denied')]:
            denied(name, lambda i=identity,p=password,v=vhost: broker_connect(i,p,v), (errors.ProbableAuthenticationError, errors.ProbableAccessDeniedError))
        denied('plaintext-amqp-listener-disabled', lambda: broker_connect('publisher', tls=False), errors.AMQPConnectionError)
        with broker_connect('consumer') as conn:
            channel = conn.channel(); channel.confirm_delivery()
            denied('consumer-cannot-publish', lambda: channel.basic_publish(exchange='events', routing_key='witness', body=b'forbidden'), errors.ChannelClosedByBroker, {403})
        # Publish uses confirms so authorization failures are synchronous.
        with broker_connect('publisher') as conn:
            channel = conn.channel(); channel.confirm_delivery()
            denied('publisher-cannot-consume', lambda: channel.basic_get('deliveries'), errors.ChannelClosedByBroker, {403})
        with broker_connect('publisher') as conn:
            channel = conn.channel(); channel.confirm_delivery()
            denied('publisher-cannot-configure-topology', lambda: channel.queue_declare('forbidden', durable=True), errors.ChannelClosedByBroker, {403})
        with broker_connect('publisher') as conn:
            channel = conn.channel(); channel.confirm_delivery()
            channel.basic_publish('events', 'witness', PAYLOAD, properties=pika.BasicProperties(delivery_mode=2, message_id='restart-witness'), mandatory=True)
            check('publisher-confirmed-durable-message', True)
        # Deliberately close without acknowledgement; delivery must remain durable.
        with broker_connect('consumer') as conn:
            method, props, body = conn.channel().basic_get('deliveries', auto_ack=False)
            check('unacknowledged-delivery-bytes', method is not None and body == PAYLOAD and props.message_id == 'restart-witness')
        return {'message_sha256': hashlib.sha256(PAYLOAD).hexdigest()}
    with broker_connect('consumer') as conn:
        channel = conn.channel(); method, props, body = channel.basic_get('deliveries', auto_ack=False)
        check('restart-retains-unacknowledged-message', method is not None and body == PAYLOAD and props.message_id == 'restart-witness')
        check('restart-redelivery-flag', bool(method.redelivered))
        channel.basic_ack(method.delivery_tag)
        check('acknowledgement-removes-delivery', channel.basic_get('deliveries')[0] is None)
    return {}


def s3(identity='assurance', password=None):
    import boto3
    from botocore.config import Config
    return boto3.client('s3', endpoint_url=os.environ['S3_ENDPOINT'], aws_access_key_id='p01root' if identity == 'root' else identity, aws_secret_access_key=password or secret(identity+'-password'), region_name='us-east-1', verify=CA, config=Config(signature_version='s3v4', connect_timeout=2, read_timeout=3, retries={'max_attempts': 0}, s3={'addressing_style': 'path'}))


def s3_wait():
    client = s3('root')
    deadline = time.monotonic()+60
    while True:
        try:
            client.list_buckets(); return client
        except Exception:
            if time.monotonic() >= deadline: raise
            time.sleep(0.5)


def evidence(stage, state):
    from botocore.exceptions import ClientError, EndpointConnectionError, ConnectionClosedError, ConnectTimeoutError, ReadTimeoutError
    if stage == 'evidence-ready':
        s3_wait();check('evidence-server-authenticated-ready',True);return {}
    if stage == 'evidence-bootstrap':
        client = s3_wait()
        client.create_bucket(Bucket=BUCKET, ObjectLockEnabledForBucket=True)
        client.put_object_lock_configuration(Bucket=BUCKET, ObjectLockConfiguration={'ObjectLockEnabled': 'Enabled', 'Rule': {'DefaultRetention': {'Mode': 'COMPLIANCE', 'Days': 1}}})
        check('bucket-versioning-enabled', client.get_bucket_versioning(Bucket=BUCKET)['Status'] == 'Enabled')
        check('default-compliance-retention-enabled', client.get_object_lock_configuration(Bucket=BUCKET)['ObjectLockConfiguration']['Rule']['DefaultRetention'] == {'Mode':'COMPLIANCE', 'Days':1})
        return {}
    if stage == 'evidence-admin-denial':
        client = s3('root')
        denied('root-cannot-delete-retained-version', lambda: client.delete_object(Bucket=BUCKET, Key=KEY, VersionId=state['version_id']), ClientError, {'InvalidRequest'}, worm=True)
        denied('root-cannot-shorten-compliance-retention', lambda: client.put_object_retention(Bucket=BUCKET, Key=KEY, VersionId=state['version_id'], Retention={'Mode':'COMPLIANCE', 'RetainUntilDate': datetime.now(timezone.utc)+timedelta(minutes=5)}), ClientError, {'InvalidRequest'}, worm=True)
        check('retention-denials-preserve-object',hashlib.sha256(client.get_object(Bucket=BUCKET,Key=KEY,VersionId=state['version_id'])['Body'].read()).hexdigest()==state['sha256'])
        retained=client.get_object_retention(Bucket=BUCKET,Key=KEY,VersionId=state['version_id'])['Retention']
        check('retention-denials-preserve-deadline',retained['Mode']==state['retention_mode'] and retained['RetainUntilDate']==datetime.fromisoformat(state['retain_until']))
        return {}
    client = s3()
    if stage == 'evidence-outage':
        denied('evidence-outage-is-visible', lambda: client.get_object(Bucket=BUCKET,Key=KEY), (EndpointConnectionError,ConnectionClosedError,ConnectTimeoutError,ReadTimeoutError))
        return {}
    if stage == 'evidence-revoked':
        denied('revoked-evidence-identity-denied', lambda: client.get_object(Bucket=BUCKET,Key=KEY), ClientError, {'InvalidAccessKeyId', 'AccessDenied'})
        return {}
    if stage == 'evidence-before':
        first = client.put_object(Bucket=BUCKET,Key=KEY,Body=PAYLOAD,ContentType='application/json')
        version = first['VersionId']
        client.put_object(Bucket=BUCKET,Key=KEY,Body=b'newer synthetic version\n')
        check('version-id-returned', bool(version) and version != 'null')
        denied('wrong-prefix-read-denied', lambda: s3('foreign').get_object(Bucket=BUCKET,Key=KEY,VersionId=version), ClientError, {'AccessDenied'})
        denied('wrong-prefix-write-denied', lambda: client.put_object(Bucket=BUCKET,Key='t_other/forbidden',Body=b'forbidden'), ClientError, {'AccessDenied'})
        denied('evidence-client-cannot-list-buckets', lambda: client.list_buckets(), ClientError, {'AccessDenied'})
        denied('evidence-client-cannot-delete-version', lambda: client.delete_object(Bucket=BUCKET,Key=KEY,VersionId=version), ClientError, {'AccessDenied'})
        denied('invalid-evidence-secret-denied', lambda: s3(password='incorrect-synthetic-secret').get_object(Bucket=BUCKET,Key=KEY), ClientError, {'SignatureDoesNotMatch', 'AccessDenied'})
        retention = client.get_object_retention(Bucket=BUCKET,Key=KEY,VersionId=version)['Retention']
        check('object-has-compliance-retention', retention['Mode'] == 'COMPLIANCE' and retention['RetainUntilDate'] > datetime.now(timezone.utc))
        return {'bucket':BUCKET,'key':KEY,'version_id':version,'sha256':hashlib.sha256(PAYLOAD).hexdigest(),'bytes':len(PAYLOAD),'retention_mode':retention['Mode'],'retain_until':retention['RetainUntilDate'].isoformat()}
    if stage == 'evidence-restore':
        body = base64.b64decode(state['base64'],validate=True)
        check('capture-digest-admission', hashlib.sha256(body).hexdigest() == state['sha256'] and len(body) == state['bytes'])
        result = client.put_object(Bucket=BUCKET,Key=KEY,Body=body,Metadata={'source-version':state['version_id'],'source-sha256':state['sha256']})
        restored = client.get_object(Bucket=BUCKET,Key=KEY,VersionId=result['VersionId'])
        check('fresh-store-restored-bytes', restored['Body'].read() == body)
        check('restore-retains-source-identity-metadata', restored['Metadata']['source-version'] == state['version_id'] and restored['Metadata']['source-sha256'] == state['sha256'])
        retained = client.get_object_retention(Bucket=BUCKET,Key=KEY,VersionId=result['VersionId'])['Retention']
        check('restore-keeps-or-extends-retention', retained['Mode'] == state['retention_mode'] and retained['RetainUntilDate'] >= datetime.fromisoformat(state['retain_until']))
        return {**{k:v for k,v in state.items() if k != 'base64'},'source_version_id':state['version_id'],'version_id':result['VersionId'],'retain_until':retained['RetainUntilDate'].isoformat()}
    deadline=time.monotonic()+45
    while True:
        try:
            obj=client.get_object(Bucket=BUCKET,Key=KEY,VersionId=state['version_id']);body=obj['Body'].read();break
        except (EndpointConnectionError,ConnectionClosedError,ConnectTimeoutError,ReadTimeoutError):
            if time.monotonic()>=deadline:raise
            time.sleep(0.5)
    check('restart-pinned-version-digest-equality', hashlib.sha256(body).hexdigest() == state['sha256'] and len(body) == state['bytes'])
    if stage == 'evidence-capture':
        check('latest-version-does-not-replace-pinned-evidence', client.get_object(Bucket=BUCKET,Key=KEY)['Body'].read() != body)
    return {**state,'base64':base64.b64encode(body).decode()}


async def temporal_connect(identity='lifecycle', namespace='lifecycle'):
    from temporalio.client import Client
    from temporalio.service import TLSConfig
    # GetSystemInfo is an explicitly public health API in the default authorizer.
    # Attach the test identity after negotiation so denials are measured on the
    # protected namespace RPC, with the SDK's structured status available.
    client=await asyncio.wait_for(Client.connect('temporal:7233',namespace=namespace,tls=TLSConfig(server_root_ca_cert=Path(CA).read_bytes(),domain='temporal')),5)
    client.rpc_metadata={} if identity=='missing' else {'authorization':'Bearer '+secret('jwt-'+identity)}
    return client


async def temporal(stage, state):
    from temporalio.api.workflowservice.v1 import RegisterNamespaceRequest, DescribeNamespaceRequest, ListWorkflowExecutionsRequest
    from google.protobuf.duration_pb2 import Duration
    from temporalio.service import RPCError, RPCStatusCode
    from temporalio.worker import Worker
    from workflow import RestartWitness
    async def describe(client):
        return await client.workflow_service.describe_namespace(DescribeNamespaceRequest(namespace='lifecycle'),timeout=timedelta(seconds=3))
    def transport_failure(error):
        detail=str(error).lower()
        return isinstance(error,TimeoutError) or (detail.startswith('failed client connect:') and any(word in detail for word in ('transport error','connecterror','tcp connect','dns error','connection refused')))
    async def rejection(name, client, codes):
        try: await describe(client)
        except RPCError as error: check(name,error.status in codes,{'status':error.status.name})
        else: check(name,False)
    if stage=='temporal-outage':
        try: client=await temporal_connect()
        except (RuntimeError,TimeoutError) as error:
            check('temporal-outage-visible',transport_failure(error),{'error_type':type(error).__name__,'phase':'connection','detail':str(error)})
        else:
            await rejection('temporal-outage-visible',client,{RPCStatusCode.UNAVAILABLE,RPCStatusCode.DEADLINE_EXCEEDED})
        return {}
    if stage=='temporal-bootstrap':
        deadline=time.monotonic()+100
        while True:
            try:
                client=await temporal_connect('admin')
                await client.workflow_service.register_namespace(RegisterNamespaceRequest(namespace='lifecycle',workflow_execution_retention_period=Duration(seconds=86400)),timeout=timedelta(seconds=4))
                break
            except RPCError as error:
                if error.status==RPCStatusCode.ALREADY_EXISTS:raise
                if time.monotonic()>=deadline:raise
            except (RuntimeError,TimeoutError) as error:
                if not transport_failure(error) or time.monotonic()>=deadline:raise
            await asyncio.sleep(0.5)
        check('namespace-created-by-bootstrap-only',True)
        return {}
    if stage in ('temporal-after','temporal-revoked'):
        deadline=time.monotonic()+90
        while True:
            try:
                client=await temporal_connect()
                await describe(client)
                if stage=='temporal-after':break
            except RPCError as error:
                if stage=='temporal-revoked' and error.status in (RPCStatusCode.PERMISSION_DENIED,RPCStatusCode.UNAUTHENTICATED):break
                if error.status not in (RPCStatusCode.UNAVAILABLE,RPCStatusCode.DEADLINE_EXCEEDED):raise
            except (RuntimeError,TimeoutError) as error:
                if not transport_failure(error):raise
            if time.monotonic()>=deadline:raise TimeoutError('Workflow restart did not reach expected state')
            await asyncio.sleep(0.5)
    else:
        client=await temporal_connect()
    if stage=='temporal-revoked':
        await rejection('temporal-revoked-visible',client,{RPCStatusCode.PERMISSION_DENIED,RPCStatusCode.UNAUTHENTICATED})
        return {}
    if stage=='temporal-before':
        await describe(client);check('namespace-authorized-read',True)
        for port in (7234,7235,7236,7239):closed_port('temporal',port)
        for identity in ('missing','foreign','expired','wrong-audience'):
            await rejection(identity+'-jwt-denied',await temporal_connect(identity),{RPCStatusCode.PERMISSION_DENIED,RPCStatusCode.UNAUTHENTICATED})
        try:
            await client.workflow_service.register_namespace(RegisterNamespaceRequest(namespace='forbidden',workflow_execution_retention_period=Duration(seconds=86400)),timeout=timedelta(seconds=3))
        except RPCError as error:check('worker-cannot-administer-namespaces',error.status==RPCStatusCode.PERMISSION_DENIED,{'status':error.status.name})
        else:check('worker-cannot-administer-namespaces',False)
        async with Worker(client,task_queue='p01-restart',workflows=[RestartWitness]):
            handle=await client.start_workflow(RestartWitness.run,'synthetic durable marker',id='p01-restart-witness',task_queue='p01-restart',execution_timeout=timedelta(minutes=15))
            check('workflow-reached-durable-wait',await asyncio.wait_for(handle.query(RestartWitness.waiting),30))
            return {'workflow_id':handle.id,'run_id':handle.first_execution_run_id,'marker':'synthetic durable marker'}
    async with Worker(client,task_queue='p01-restart',workflows=[RestartWitness]):
        handle=client.get_workflow_handle(state['workflow_id'],run_id=state['run_id'])
        check('restarted-workflow-still-waiting',await asyncio.wait_for(handle.query(RestartWitness.waiting),45))
        await handle.signal(RestartWitness.release)
        result=await asyncio.wait_for(handle.result(),45)
        check('restarted-workflow-completes-same-execution',result==state['marker'],{'run_id':state['run_id'],'result':result})
    deadline=time.monotonic()+30
    while True:
        visible=await client.workflow_service.list_workflow_executions(ListWorkflowExecutionsRequest(namespace='lifecycle',query="WorkflowId = 'p01-restart-witness'",page_size=10),timeout=timedelta(seconds=3))
        matches=[e for e in visible.executions if e.execution.run_id==state['run_id'] and e.status==2]
        if matches:break  # WorkflowExecutionStatus.COMPLETED is protobuf value 2.
        if time.monotonic()>=deadline:raise TimeoutError('Completed execution missing from visibility')
        await asyncio.sleep(0.5)
    check('completed-execution-in-private-visibility-store',len(matches)==1,{'run_id':matches[0].execution.run_id,'status':matches[0].status})
    return state


def database():
    import psycopg
    def connect(name='temporal',db='temporal',password=None,sslmode='verify-full'):
        return psycopg.connect(host='postgres',dbname=db,user=name+'_runtime',password=password or secret(name+'-runtime-password'),sslmode=sslmode,sslrootcert=CA,connect_timeout=3,autocommit=True)
    with connect() as conn:
        row=conn.execute('SELECT ssl,version FROM pg_stat_ssl WHERE pid=pg_backend_pid()').fetchone()
        check('temporal-database-verified-tls',row[0] and row[1] in ('TLSv1.2','TLSv1.3'),row)
        check('temporal-schema-version-readable',bool(conn.execute('SELECT curr_version FROM schema_version').fetchone()[0]))
        for name,sql in [('runtime-ddl-denied','CREATE TABLE forbidden(id int)'),('runtime-ownership-escalation-denied','SET ROLE temporal_migrator')]:
            denied(name,lambda q=sql:conn.execute(q),psycopg.errors.InsufficientPrivilege)
    denied('wrong-private-database-denied',lambda:connect(db='temporal_visibility'),psycopg.OperationalError)
    denied('invalid-database-secret-denied',lambda:connect(password='incorrect-synthetic-password'),psycopg.OperationalError)
    denied('plaintext-database-connection-denied',lambda:connect(sslmode='disable'),psycopg.OperationalError)
    with connect('visibility','temporal_visibility') as conn:
        check('visibility-schema-version-readable',bool(conn.execute('SELECT curr_version FROM schema_version').fetchone()[0]))
        check('visibility-conversion-function-executable',conn.execute("SELECT convert_ts('2026-10-05T00:00:00Z')").fetchone()[0].isoformat()=='2026-10-05T00:00:00')
        check('visibility-function-not-public-or-foreign',not conn.execute("SELECT has_function_privilege('temporal_runtime','public.convert_ts(character varying)','EXECUTE')").fetchone()[0])
    return {}


def main():
    stage=sys.argv[1]
    state=json.load(sys.stdin) if stage in ('temporal-after','evidence-admin-denial','evidence-capture','evidence-restore','evidence-after') else None
    try:
        if stage.startswith('broker-'): result=broker(stage)
        elif stage.startswith('temporal-'): result=asyncio.run(temporal(stage,state))
        elif stage.startswith('evidence-'): result=evidence(stage,state)
        elif stage=='database': result=database()
        else: raise ValueError('Unknown probe stage')
    except Exception as error:
        print(json.dumps({'stage':stage,'result':'FAIL','checks':CHECKS,'error_type':type(error).__name__,'error':str(error)}))
        raise SystemExit(1)
    print(json.dumps({'stage':stage,'result':'PASS','checks':CHECKS,'state':result}))


if __name__=='__main__': main()
