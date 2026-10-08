"""Typed subset used by Inventory's pinned pika 1.4.4 adapter."""

from ssl import SSLContext

class PlainCredentials:
    def __init__(self, username: str, password: str) -> None: ...

class SSLOptions:
    def __init__(self, context: SSLContext, server_hostname: str) -> None: ...

class ConnectionParameters:
    def __init__(
        self,
        *,
        host: str,
        port: int,
        virtual_host: str,
        credentials: PlainCredentials,
        ssl_options: SSLOptions,
        socket_timeout: float,
        stack_timeout: float,
        blocked_connection_timeout: float,
        connection_attempts: int,
        heartbeat: int,
    ) -> None: ...

class BasicProperties:
    def __init__(
        self, *, content_type: str, delivery_mode: int, message_id: str, user_id: str, type: str
    ) -> None: ...

class BlockingChannel:
    def confirm_delivery(self) -> None: ...
    def basic_publish(
        self,
        *,
        exchange: str,
        routing_key: str,
        body: bytes,
        properties: BasicProperties,
        mandatory: bool,
    ) -> None: ...

class BlockingConnection:
    def __init__(self, parameters: ConnectionParameters) -> None: ...
    def channel(self) -> BlockingChannel: ...
    def close(self) -> None: ...
