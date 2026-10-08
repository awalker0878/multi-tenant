"""Delivery entrypoint receives its dependency from composition."""

from probe_inventory.application.advance import SampleStore, advance
from probe_inventory.domain.sample import Sample


def execute(label: str, store: SampleStore) -> Sample:
    return advance(Sample(label), store)
