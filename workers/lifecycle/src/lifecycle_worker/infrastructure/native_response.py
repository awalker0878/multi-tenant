"""Bounded, complete native replies with authority checked through the final byte."""

import http.client
import re
import time
from collections.abc import Callable

from lifecycle_worker.application.native import NativeHeld


def response_bytes(
    response: http.client.HTTPResponse,
    limit: int,
    timeout: float,
    current: Callable[[], None],
) -> bytes:
    deadline = time.monotonic() + timeout
    length = response.getheader("Content-Length")
    transfer = response.getheader("Transfer-Encoding")
    if (
        length is not None and (re.fullmatch(r"[0-9]{1,16}", length) is None or int(length) > limit)
    ) or (transfer is not None and (transfer.lower() != "chunked" or length is not None)):
        raise NativeHeld("native_response_framing_invalid")
    expected = None if length is None else int(length)
    result = bytearray()

    def checked() -> None:
        current()
        if time.monotonic() >= deadline:
            raise NativeHeld("native_response_deadline")

    while True:
        checked()
        part = response.read1(min(65536, limit + 1 - len(result)))
        checked()
        result.extend(part)
        if len(result) > limit:
            raise NativeHeld("native_response_bound")
        if not part:
            # HTTPResponse.read1 can return EOF before a declared Content-Length.
            # A syntactically valid JSON prefix is still an incomplete response.
            if expected is not None and len(result) != expected:
                raise NativeHeld("native_response_incomplete")
            return bytes(result)
