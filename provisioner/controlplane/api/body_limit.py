"""Bound the full HTTP body before FastAPI parses JSON.

The limit counts ASGI body bytes, so chunked requests and understated
Content-Length cannot evade it. It applies to every route, including future
ones, and should also be enforced at the ingress proxy.
"""
from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any


class BodyLimitMiddleware:
    def __init__(self, app: Callable, *, max_body_bytes: int) -> None:
        if type(max_body_bytes) is not int or max_body_bytes < 1:
            raise ValueError('max_body_bytes must be a positive integer')
        self.app = app
        self.max_body_bytes = max_body_bytes

    async def __call__(self, scope: dict, receive: Callable, send: Callable) -> None:
        if scope['type'] != 'http':
            await self.app(scope, receive, send)
            return

        lengths = [value for key, value in scope.get('headers', ())
                   if key.lower() == b'content-length']
        if len(lengths) > 1:
            await self._error(send, 400, 'INVALID_CONTENT_LENGTH', 'Ambiguous request length')
            return
        if lengths:
            try:
                length = int(lengths[0])
            except ValueError:
                await self._error(send, 400, 'INVALID_CONTENT_LENGTH', 'Invalid request length')
                return
            if length < 0:
                await self._error(send, 400, 'INVALID_CONTENT_LENGTH', 'Invalid request length')
                return
            if length > self.max_body_bytes:
                await self._error(send, 413, 'REQUEST_TOO_LARGE', 'Request body exceeds the configured limit')
                return

        # Read before routing: a GET handler may never ask to receive its body.
        # A fixed buffer is safe here because the upper bound is checked on
        # every ASGI chunk, independent of Content-Length.
        body = bytearray()
        while True:
            message = await receive()
            if message['type'] == 'http.disconnect':
                return
            if message['type'] != 'http.request':
                continue
            chunk = message.get('body', b'')
            if len(body) + len(chunk) > self.max_body_bytes:
                await self._error(send, 413, 'REQUEST_TOO_LARGE',
                                  'Request body exceeds the configured limit')
                return
            body.extend(chunk)
            if not message.get('more_body', False):
                break

        replayed = False

        async def replay_receive() -> dict[str, Any]:
            nonlocal replayed
            if not replayed:
                replayed = True
                return {'type': 'http.request', 'body': bytes(body),
                        'more_body': False}
            return await receive()

        await self.app(scope, replay_receive, send)

    @staticmethod
    async def _error(send: Callable, status: int, code: str, message: str) -> None:
        body = json.dumps({'error': {'code': code, 'message': message}},
                          separators=(',', ':')).encode('utf-8')
        await send({'type': 'http.response.start', 'status': status,
                    'headers': [(b'content-type', b'application/json'),
                                (b'content-length', str(len(body)).encode('ascii')),
                                (b'cache-control', b'no-store')]})
        await send({'type': 'http.response.body', 'body': body})
