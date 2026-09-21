"""Durable ordered events for a single owned resource; not a native writer fence."""
from contextlib import contextmanager
import fcntl
import os
from pathlib import Path
from tools import readback_core as c
from tools.run_files import (encoded, digest, load_private, private_path, require,
                             sync_directory, write_new)


class Journal:
    def __init__(self, directory, scope):
        self.directory = directory
        self.scope = scope
        self.events = []
        previous = None
        files = sorted(directory.glob('*.json'))
        for number, path in enumerate(files, 1):
            require(path.name == f'{number:08d}.json', 'Execution journal sequence is incomplete')
            event = load_private(path)
            c.exact_keys(event, {'format', 'sequence', 'scope', 'previous_sha256', 'at', 'kind', 'data'})
            require(event['format'] == 'hosting-execution-event/1' and type(event['sequence']) is int
                    and event['sequence'] == number and event['scope'] == scope
                    and event['previous_sha256'] == previous, 'Execution journal chain differs')
            c.identifier(event['kind'])
            require(isinstance(event['data'], dict), 'Execution event data must be an object')
            require(c.timestamp(event['at']) <= c.timestamp(c.now()), 'Future execution event')
            if self.events:
                require(c.timestamp(self.events[-1]['at']) <= c.timestamp(event['at']), 'Execution clock regressed')
            self.events.append(event)
            previous = digest(encoded(event))

    def append(self, kind, data):
        c.identifier(kind)
        require(isinstance(data, dict), 'Execution event data must be an object')
        event = dict(format='hosting-execution-event/1', sequence=len(self.events) + 1,
                     scope=self.scope, previous_sha256=digest(encoded(self.events[-1])) if self.events else None,
                     at=c.now(), kind=kind, data=data)
        if self.events:
            require(c.timestamp(self.events[-1]['at']) <= c.timestamp(event['at']), 'Execution clock regressed')
        write_new(self.directory / f'{event["sequence"]:08d}.json', encoded(event))
        self.events.append(event)
        return event


@contextmanager
def locked(ledger, scope):
    """All controllers sharing this ledger serialize; distributed exclusion is external."""
    parent = private_path(ledger, directory=True)
    directory = parent / digest(encoded(scope))
    try:
        directory.mkdir(mode=0o700)
        sync_directory(parent)
    except FileExistsError:
        private_path(directory, directory=True)
    descriptor = os.open(directory / 'writer.lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        private_path(directory / 'writer.lock')
        fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield Journal(directory, scope)
    finally:
        os.close(descriptor)
