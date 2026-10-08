"""A broker acknowledgement must never precede the owning durable commit."""

from unittest.mock import MagicMock

import pytest
from psycopg.pq import TransactionStatus

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
