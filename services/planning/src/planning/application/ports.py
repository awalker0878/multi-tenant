"""Planning-owned ports; owners expose read contracts, never sibling databases."""

from collections.abc import Sequence
from contextlib import AbstractContextManager
from typing import Any, Protocol

from planning.domain.model import Actor


class Transaction(Protocol):
    def execute(self, sql: str, parameters: Sequence[Any] = ()) -> None: ...
    def one(self, sql: str, parameters: Sequence[Any] = ()) -> dict[str, Any] | None: ...
    def all(self, sql: str, parameters: Sequence[Any] = ()) -> list[dict[str, Any]]: ...


class Database(Protocol):
    def transaction(self) -> AbstractContextManager[Transaction]: ...


class Sources(Protocol):
    def resolve(
        self,
        actor: Actor,
        revision: str,
        candidates: list[dict[str, Any]],
        delegations: dict[str, str],
        action: str,
        method: str,
    ) -> tuple[dict[str, Any], list[dict[str, Any]]]: ...


class Authority(Protocol):
    def caller(self, credential: str, audience: str = "console") -> None: ...
    def actor(
        self,
        credential: str,
        delegation: str,
        tenant: str,
        action: str,
        application: str,
        environment: str,
        site: str,
    ) -> Actor: ...
