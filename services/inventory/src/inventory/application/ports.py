"Inventory-owned boundaries; no sibling database or framework types cross these ports."

from collections.abc import Mapping, Sequence
from contextlib import AbstractContextManager
from typing import Any, Protocol

from inventory.domain.discovery import Actor, EnrollmentPolicy, Worker


class Transaction(Protocol):
    def execute(self, sql: str, parameters: Sequence[Any] = ()) -> None: ...
    def one(self, sql: str, parameters: Sequence[Any] = ()) -> dict[str, Any] | None: ...
    def all(self, sql: str, parameters: Sequence[Any] = ()) -> list[dict[str, Any]]: ...


class Database(Protocol):
    def transaction(self) -> AbstractContextManager[Transaction]: ...


class Policies(Protocol):
    def load(self) -> Mapping[str, EnrollmentPolicy]: ...


class Authority(Protocol):
    def actor(
        self, credential: str, delegation: str, tenant: str, action: str, site: str | None
    ) -> Actor: ...
    def worker(self, credential: str) -> Worker: ...
