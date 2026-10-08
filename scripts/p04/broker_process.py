"""Disposable independent AMQPS observer and post-confirm process-loss injection."""
import json
import os
from pathlib import Path
import ssl
import sys

import pika
from inventory.application.events import publish_one
from inventory.infrastructure.publisher import publish
from inventory.infrastructure.store import Postgres

if os.environ.get('GITHUB_ACTIONS') != 'true' or os.environ.get('P04_TEST_POSTGRES') != '1':
    raise SystemExit(2)

if sys.argv[1] == 'uncertain':
    def accepted_then_lost(fact):
        publish(fact)
        raise RuntimeError('synthetic process loss after confirmed publish')
    try:
        publish_one(Postgres(), accepted_then_lost)
    except RuntimeError:
        print('Accepted native broker message; database receipt rolled back.')
        raise SystemExit(75)
    raise SystemExit(1)

if sys.argv[1] != 'observe':
    raise SystemExit(2)
connection = pika.BlockingConnection(pika.ConnectionParameters(
    host='127.0.0.1', port=5679, virtual_host='product',
    credentials=pika.PlainCredentials('p04-observer', Path(os.environ['P04_OBSERVER_PASSWORD_FILE']).read_text()),
    ssl_options=pika.SSLOptions(ssl.create_default_context(cafile=os.environ['INVENTORY_BROKER_CA_FILE']), '127.0.0.1'),
    socket_timeout=3, stack_timeout=5, blocked_connection_timeout=3))
events = []
try:
    channel = connection.channel()
    for _ in range(1000):
        method, properties, body = channel.basic_get(queue='p04.observer', auto_ack=False)
        if method is None:
            break
        events.append({'body': json.loads(body), 'message_id': properties.message_id,
                       'user_id': properties.user_id, 'routing_key': method.routing_key,
                       'content_type': properties.content_type, 'delivery_mode': properties.delivery_mode})
        channel.basic_ack(delivery_tag=method.delivery_tag)
    else:
        raise RuntimeError('observer bound')
finally:
    connection.close()
Path(sys.argv[2]).write_text(json.dumps(events, indent=2)+'\n')
print('Observed', len(events), 'messages through a separately authorized AMQPS consumer.')
