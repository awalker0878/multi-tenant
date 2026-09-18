#!/usr/bin/env python3
"""Retired source-block amendment entry point: always stop before any write.

Main uses immutable transcriptions and separately maintained docs/current records.
The previous alternate amendment ledger is retained empty for historical provenance,
not as an active means of overriding a source paragraph or claiming acceptance.
"""
import sys


def proposed(*args, **kwargs):
    raise ValueError('Source-block amendments are not active: use docs/current and sources/documentation/current_design_records.json; no file was changed')


def main():
    print('RETIRED_AUTHORING_MODEL: no writes performed. See docs/current/README.md and docs/assurance/main-integration-audit.md.', file=sys.stderr)
    return 2


if __name__=='__main__':
    raise SystemExit(main())
