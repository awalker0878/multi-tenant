"""Mandatory AMQPS publication with publisher confirms and a dedicated producer identity."""

import os
import ssl
from typing import Any

import pika

from inventory.domain.discovery import canonical
from inventory.infrastructure.foundation import mounted_secret, required


def publish(fact: dict[str, Any]) -> None:
    host = required("INVENTORY_BROKER_HOST")
    port = int(required("INVENTORY_BROKER_PORT"))
    ca = required("INVENTORY_BROKER_CA_FILE")
    if not 1 <= port <= 65535 or not os.path.isabs(ca):
        raise ValueError("Invalid broker trust")
    connection = pika.BlockingConnection(
        pika.ConnectionParameters(
            host=host,
            port=port,
            virtual_host="product",
            credentials=pika.PlainCredentials(
                "inventory", mounted_secret("INVENTORY_BROKER_PASSWORD_FILE")
            ),
            ssl_options=pika.SSLOptions(ssl.create_default_context(cafile=ca), host),
            socket_timeout=2,
            stack_timeout=4,
            blocked_connection_timeout=3,
            connection_attempts=1,
            heartbeat=10,
        )
    )
    try:
        channel = connection.channel()
        channel.confirm_delivery()
        channel.basic_publish(
            exchange="inventory.events",
            routing_key="inventory.facts.v1",
            body=canonical(fact).encode(),
            mandatory=True,
            properties=pika.BasicProperties(
                content_type="application/json",
                delivery_mode=2,
                message_id=fact["event_id"],
                user_id="inventory",
                type=fact["event_type"],
            ),
        )
    finally:
        connection.close()
