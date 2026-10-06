"""Independent E2 broker observer and loss after a genuine publisher confirmation."""
import json
import os
from pathlib import Path
import ssl
import sys
import pika
from planning.application.events import publish_one
from planning.infrastructure.facts.broker import publish
from planning.infrastructure.store import Postgres

if os.environ.get('GITHUB_ACTIONS')!='true' or os.environ.get('P05_TEST_POSTGRES')!='1':raise SystemExit(2)
if sys.argv[1]=='uncertain':
    def lost(fact):
        publish(fact)
        raise RuntimeError('synthetic process loss after broker confirmation')
    try:publish_one(Postgres(),lost)
    except RuntimeError:raise SystemExit(75)
    raise SystemExit(1)
if sys.argv[1]!='observe':raise SystemExit(2)
conn=pika.BlockingConnection(pika.ConnectionParameters(host='127.0.0.1',port=5679,virtual_host='product',credentials=pika.PlainCredentials('p04-observer',Path(os.environ['P04_OBSERVER_PASSWORD_FILE']).read_text()),ssl_options=pika.SSLOptions(ssl.create_default_context(cafile=os.environ['PLANNING_BROKER_CA_FILE']),'127.0.0.1'),socket_timeout=3,stack_timeout=5,blocked_connection_timeout=3))
rows=[]
try:
    channel=conn.channel()
    for _ in range(1000):
        method,props,body=channel.basic_get('p05.observer',auto_ack=False)
        if method is None:break
        rows.append({'body':json.loads(body),'message_id':props.message_id,'user_id':props.user_id,'routing_key':method.routing_key})
        assert props.user_id=='planning' and props.message_id==rows[-1]['body']['event_id']
        channel.basic_ack(method.delivery_tag)
finally:conn.close()
Path(sys.argv[2]).write_text(json.dumps(rows,indent=2)+'\n')
print('Independently observed',len(rows),'confirmed Planning facts.')
