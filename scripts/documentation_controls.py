"""Deprecated import names for the one maintained ADR implementation.

The block-amendment publication model was not retained when main adopted immutable
transcriptions plus docs/current. These aliases use the CURRENT record format; old
acceptance fields are intentionally rejected. No second renderer or writer exists.
See docs/assurance/main-integration-audit.md for the consolidation decision.
"""
from adr_lifecycle import validate as lifecycle_errors, render
from documentation_structure import visible


def adr_text(builder, record):
    return render(record, builder)


def visible_word(node, code=False):
    value=visible(node)
    return value if code else ' '.join(value.split())


def retired_model(*args, **kwargs):
    raise ValueError('Retired source-block amendment model: edit docs/current with its owner/version record; frozen transcriptions remain unchanged')


region=retired_model
block_checks=retired_model
amendment_records=retired_model
render_adrs=retired_model
