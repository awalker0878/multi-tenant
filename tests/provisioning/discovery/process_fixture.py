"""Bounded readiness for real process fixtures; never an application/authority shim.

Starting an interpreter is not the operation under test. A child calls
fixture_ready() after imports/setup, then waits for explicit activation. Parents
can prepare competing workers before a five-second lock/exclusion scenario starts.
All subsequent operation deadlines and actual application checks stay in force.
"""
from __future__ import annotations

import select
import subprocess
import sys

_READY = 'HOSTING_TEST_PROCESS_READY'
_PREAMBLE = '''
import select as _fixture_select, sys as _fixture_sys

def fixture_ready():
    print('HOSTING_TEST_PROCESS_READY', flush=True)
    if (not _fixture_select.select([_fixture_sys.stdin], [], [], 30)[0]
            or _fixture_sys.stdin.readline() != 'RUN\\n'):
        raise RuntimeError('Fixture activation timed out or was invalid')
'''


def start_prepared(program: str, arguments: list[str]) -> subprocess.Popen:
    """Start a fixed test program and require readiness, not a successful effect."""
    process = subprocess.Popen([sys.executable, '-c', _PREAMBLE + program, *arguments],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        if (not select.select([process.stdout], [], [], 30)[0]
                or process.stdout.readline().strip() != _READY):
            raise AssertionError('Fixture did not report interpreter/setup readiness')
        return process
    except BaseException:
        if process.poll() is None:
            process.kill()
        process.communicate(timeout=5)
        raise


def activate(process: subprocess.Popen) -> None:
    """Release only this prepared child; readiness never counts as an effect."""
    if process.poll() is not None:
        raise AssertionError('Prepared process exited before activation')
    process.stdin.write('RUN\n')
    process.stdin.flush()
