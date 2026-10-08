"""Independent service composition root."""

from probe_planning.interfaces.command import read


def probe() -> str:
    return read()
