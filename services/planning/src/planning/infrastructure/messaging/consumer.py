"""One bounded delivery from the dedicated, broker-authorized Catalogue route."""

from typing import Any

from jsonschema.exceptions import ValidationError

from planning.infrastructure.messaging.inbox import Inbox


def consume_one(channel: Any, inbox: Inbox, tenants: frozenset[str]) -> str:
    method, properties, body = channel.basic_get("planning.facts", auto_ack=False)
    if method is None:
        return "empty"
    try:
        if properties.user_id != "catalogue" or properties.content_type != "application/json":
            raise ValueError("producer_denied")
        result = inbox.accept(body, "catalogue", tenants)
    except (ValueError, ValidationError, UnicodeError):
        channel.basic_reject(method.delivery_tag, requeue=False)
        return "quarantined"
    except Exception:
        # The quorum queue's delivery-limit bounds redelivery. No nested retry loop.
        channel.basic_nack(method.delivery_tag, requeue=True)
        raise
    channel.basic_ack(method.delivery_tag)
    return str(result)
