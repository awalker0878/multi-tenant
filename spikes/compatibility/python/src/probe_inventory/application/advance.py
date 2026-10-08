"""Synthetic use case depends on its owned domain and port."""

from typing import Protocol

from probe_inventory.domain.sample import Sample


class SampleStore(Protocol):
    def save(self, sample: Sample) -> None: ...


def advance(sample: Sample, store: SampleStore) -> Sample:
    updated = sample.advance()
    store.save(updated)
    return updated
