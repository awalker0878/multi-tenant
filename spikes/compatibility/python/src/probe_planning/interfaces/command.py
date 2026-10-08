"""Interface imports its owned application."""

from probe_planning.application.describe import execute


def read() -> str:
    return execute()
