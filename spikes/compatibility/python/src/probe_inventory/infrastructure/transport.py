"""A transport library is legal in an owned adapter."""

import httpx


def host() -> str:
    return httpx.URL("https://compatibility.invalid").host
