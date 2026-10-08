"""A broker acknowledgement must never precede the owning durable commit."""

import json
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from psycopg.pq import TransactionStatus

from planning.infrastructure.messaging.codec import decode
from planning.infrastructure.messaging.consumer import consume_one
from planning.infrastructure.messaging.inbox import Inbox


@pytest.mark.parametrize(
    "autocommit,status", [(False, TransactionStatus.IDLE), (True, TransactionStatus.INTRANS)]
)
def test_inbox_rejects_outer_transaction_before_reading_or_writing(
    autocommit: bool, status: TransactionStatus
) -> None:
    database = MagicMock()
    database.autocommit = autocommit
    database.info.transaction_status = status
    with pytest.raises(RuntimeError, match="inbox_requires_idle_autocommit_connection"):
        Inbox(database).accept(b"{}", "catalogue", frozenset({"tenant_a"}))
    database.execute.assert_not_called()
    database.transaction.assert_not_called()


def event() -> bytes:
    return json.dumps(
        {
            "event_type": "catalogue.foundation.recorded",
            "schema_version": 1,
            "event_id": str(uuid4()),
            "correlation_id": str(uuid4()),
            "tenant_id": "tenant_a",
            "actor_id": "actor_a",
            "record_id": "record_a",
            "revision": "1",
            "payload_sha256": "a" * 64,
            "source_revision": "b" * 40,
            "occurred_at": "2026-10-08T00:00:00Z",
        }
    ).encode()


def test_foundation_message_retains_valid_wire_support() -> None:
    assert decode(event()).tenant_id == "tenant_a"


@pytest.mark.parametrize("fault", ["duplicate_key", "deep_nesting"])
def test_ambiguous_or_deep_foundation_message_is_quarantined(fault: str) -> None:
    wire = (
        b'{"tenant_id":"foreign",' + event()[1:]
        if fault == "duplicate_key"
        else b'{"nested":' + b"[" * 1500 + b"]" * 1500 + b"}"
    )
    database = MagicMock()
    database.autocommit = True
    database.info.transaction_status = TransactionStatus.IDLE
    channel = MagicMock()
    delivery, properties = MagicMock(), MagicMock()
    properties.user_id, properties.content_type = "catalogue", "application/json"
    channel.basic_get.return_value = (delivery, properties, wire)
    assert consume_one(channel, Inbox(database), frozenset({"tenant_a"})) == "quarantined"
    channel.basic_reject.assert_called_once_with(delivery.delivery_tag, requeue=False)
    channel.basic_ack.assert_not_called()
    channel.basic_nack.assert_not_called()
    database.transaction.assert_not_called()
