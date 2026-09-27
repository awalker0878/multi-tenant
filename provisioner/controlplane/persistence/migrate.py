"""Apply packaged PostgreSQL migrations with one transactional advisory lock.

Run with an independently provisioned migration role. It must never be the
service's runtime role. The runtime uses no DDL permission.
"""
from __future__ import annotations

import hashlib
import re
from importlib import resources
from typing import Callable


def apply_migrations(connection_factory: Callable) -> list[str]:
    if not callable(connection_factory):
        raise TypeError('A PostgreSQL migration connection factory is required')
    package = 'provisioner.controlplane.persistence.migrations'
    scripts = sorted((item for item in resources.files(package).iterdir()
                      if re.fullmatch(r'\d{4}_[a-z0-9_]+\.sql', item.name)),
                     key=lambda item: item.name)
    versions = [item.name.split('_', 1)[0] for item in scripts]
    if not versions or versions != [f'{number:04d}' for number in range(1, len(versions) + 1)]:
        raise RuntimeError('Packaged PostgreSQL migrations are incomplete or unordered')
    changed = []
    with connection_factory() as connection:
        # A session lock persists across separate per-file transactions. With
        # autocommit on, each ``transaction()`` has its own all-or-nothing DDL
        # and version-ledger insert; an interrupted run resumes at the next file.
        connection.autocommit = True
        connection.execute('SELECT pg_advisory_lock(1414676272, 1129141068)')
        try:
            exists = connection.execute(
                "SELECT to_regclass('hosting_controlplane.schema_migrations') IS NOT NULL"
            ).fetchone()[0]
            recorded = dict(connection.execute(
                'SELECT version, script_digest FROM hosting_controlplane.schema_migrations'
            ).fetchall()) if exists else {}
            if exists and '0001' not in recorded:
                raise RuntimeError('Existing control-plane schema has no baseline migration')
            if set(recorded) - set(versions):
                raise RuntimeError('Database has an unknown control-plane migration')
            for item, version in zip(scripts, versions):
                script = item.read_text(encoding='utf-8')
                digest = hashlib.sha256(script.encode('utf-8')).hexdigest()
                if version in recorded:
                    if recorded[version] != digest:
                        raise RuntimeError('Applied control-plane migration was modified')
                    continue
                # SQL assets are packaged and reviewed code. No request data
                # is interpolated into migration DDL.
                with connection.transaction():
                    connection.execute(script, prepare=False)
                    connection.execute(
                        'INSERT INTO hosting_controlplane.schema_migrations '
                        '(version, script_digest) VALUES (%s, %s)', (version, digest))
                changed.append(version)
        finally:
            connection.execute('SELECT pg_advisory_unlock(1414676272, 1129141068)')
    return changed


def main() -> int:
    import psycopg  # Optional controlplane extra; planning CLI does not require it.

    versions = apply_migrations(lambda: psycopg.connect())
    print('Applied PostgreSQL migrations:', ', '.join(versions) or '(none)')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
