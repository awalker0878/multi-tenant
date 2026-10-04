"""Synthetic invariant; no product schema or native effect."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Sample:
    label: str
    revision: int = 0

    def advance(self) -> "Sample":
        if self.revision < 0:
            raise ValueError("Revision cannot be negative")
        return Sample(label=self.label, revision=self.revision + 1)
