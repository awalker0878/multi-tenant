"""Composition may bind both adapters and interfaces."""

from probe_inventory.infrastructure.memory import MemoryStore
from probe_inventory.interfaces.command import execute


def probe() -> int:
    store = MemoryStore()
    execute("synthetic", store)
    return store.saved[0].revision
