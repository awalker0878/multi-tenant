"""Bounded AMQPS with authenticated producer identity and commit-before-ack semantics."""

import hashlib
import json
import os
import ssl
from importlib.resources import files
from typing import Any
from uuid import uuid4

import pika
from jsonschema import Draft202012Validator

from planning.application.planning import Planning
from planning.domain.model import Rejected, decode
from planning.infrastructure.foundation import mounted_secret, required


def connection() -> Any:
    host = required("PLANNING_BROKER_HOST")
    port = int(required("PLANNING_BROKER_PORT"))
    ca = required("PLANNING_BROKER_CA_FILE")
    if not 1 <= port <= 65535 or not os.path.isabs(ca):
        raise ValueError("invalid_broker_trust")
    return pika.BlockingConnection(
        pika.ConnectionParameters(
            host=host,
            port=port,
            virtual_host="product",
            credentials=pika.PlainCredentials(
                "planning", mounted_secret("PLANNING_BROKER_PASSWORD_FILE")
            ),
            ssl_options=pika.SSLOptions(ssl.create_default_context(cafile=ca), host),
            socket_timeout=2,
            stack_timeout=4,
            blocked_connection_timeout=3,
            connection_attempts=1,
            heartbeat=10,
        )
    )


def publish(fact: dict[str, Any]) -> None:
    conn = connection()
    try:
        channel = conn.channel()
        channel.confirm_delivery()
        channel.basic_publish(
            exchange="planning.events",
            routing_key="planning.facts.v1",
            body=json.dumps(fact, sort_keys=True, separators=(",", ":")).encode(),
            mandatory=True,
            properties=pika.BasicProperties(
                content_type="application/json",
                delivery_mode=2,
                message_id=fact["event_id"],
                user_id="planning",
                type=fact["event_type"],
            ),
        )
    finally:
        conn.close()


def consume_one(channel: Any, planning: Planning, owner: str) -> str:
    if owner not in {"inventory", "catalogue"}:
        raise ValueError("invalid_owner")
    queue = "planning.inventory" if owner == "inventory" else "planning.intent"
    method, properties, raw = channel.basic_get(queue, auto_ack=False)
    if method is None:
        return "empty"
    try:
        if (
            properties.user_id != owner
            or properties.content_type != "application/json"
            or len(raw) > 262144
        ):
            raise Rejected("producer_or_message_bound")
        event = decode(raw)
        schema = json.loads(
            files("planning.infrastructure.facts").joinpath(owner + ".json").read_text()
        )
        if (
            not Draft202012Validator(schema).is_valid(event)
            or event.get("event_id") != properties.message_id
        ):
            raise Rejected("invalid_fact_contract")
        planning.invalidate(event)
    except (Rejected, ValueError, UnicodeError):
        # Preserve poison identity without retaining arbitrary secret-bearing payloads.
        with planning.database.transaction() as tx:
            tx.execute(
                "INSERT INTO app.planning_fact_rejections(id,owner,paylo"
                "ad_digest) VALUES(%s,%s,%s)",
                (str(uuid4()), owner, hashlib.sha256(raw).hexdigest()),
            )
        channel.basic_ack(method.delivery_tag)
        return "quarantined"
    except Exception:
        channel.basic_nack(method.delivery_tag, requeue=True)
        raise
    channel.basic_ack(method.delivery_tag)
    return "committed"
