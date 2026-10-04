"""Disposable in-memory adapter; not production persistence."""

from probe_inventory.domain.sample import Sample


class MemoryStore:
    def __init__(self) -> None:
        self.saved: list[Sample] = []

    def save(self, sample: Sample) -> None:
        self.saved.append(sample)
