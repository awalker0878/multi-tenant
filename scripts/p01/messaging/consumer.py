"""Disposable invocation adapter using only the installed Planning package."""
import json
from pathlib import Path
import ssl
import sys

import pika
import psycopg
from planning.infrastructure.messaging.consumer import consume_one
from planning.infrastructure.messaging.inbox import Inbox

secret=lambda name:Path('/run/secrets/'+name).read_text().strip()
db=psycopg.connect(host='postgres',port=5432,dbname='planning',user='planning_runtime',password=secret('db-password'),sslmode='verify-full',sslrootcert='/run/secrets/ca.crt',connect_timeout=2,autocommit=True)
request=json.load(sys.stdin)
connection=pika.BlockingConnection(pika.ConnectionParameters('rabbit',5671,'product',pika.PlainCredentials('planning',secret('broker-password')),ssl_options=pika.SSLOptions(ssl.create_default_context(cafile='/run/secrets/ca.crt'),'rabbit'),socket_timeout=3,stack_timeout=6,blocked_connection_timeout=3,heartbeat=0))
try:
    channel=connection.channel()
    if request['operation']=='leave-unacked':
        method,props,body=channel.basic_get('planning.facts',auto_ack=False)
        assert method is not None
        result=Inbox(db).accept(body,props.user_id,frozenset(request['tenants']))
        print(json.dumps({'result':result,'event_id':json.loads(body)['event_id']}),flush=True)
        sys.exit(91)
    elif request['operation']=='deadletter':
        method,props,body=channel.basic_get('planning.quarantine',auto_ack=False)
        assert method is not None
        channel.basic_ack(method.delivery_tag)
        result='quarantine_received'
    else:
        result=consume_one(channel,Inbox(db),frozenset(request['tenants']))
    print(json.dumps({'result':result}))
except Exception:
    print(json.dumps({'result':'rejected','reason':'dependency_failure'}))
    sys.exit(2)
finally:
    connection.close();db.close()
