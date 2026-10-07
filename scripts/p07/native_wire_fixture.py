"""Real internal TLS routes and worker database; provider/tool/observer stay synthetic."""

from contextlib import ExitStack, contextmanager
from pathlib import Path
import secrets
import socket
import subprocess
from threading import Thread
import time

import psycopg
from psycopg.rows import dict_row
import uvicorn

from lifecycle.domain.execution import Rejected
from lifecycle.infrastructure.native_effects import NativeWorkerEndpoint, NativeWorkerEffects
from lifecycle.interfaces.native import NativeBoundaryApp
from lifecycle_worker.application.native import NativeHeld, ProcessResult
from lifecycle_worker.application.native_effect import NativeSavedPlanEffect
from lifecycle_worker.infrastructure.native_authority import LifecycleNativeBoundary
from lifecycle_worker.infrastructure.native_http import NativeEndpoint
from lifecycle_worker.infrastructure.native_journal import PostgresNativeJournal
from lifecycle_worker.interfaces.native import NativeEffectApp

ROOT = Path(__file__).resolve().parents[2]


@contextmanager
def server(app, certificate, key):
    with socket.socket() as listener:
        listener.bind(('127.0.0.1', 0))
        port = listener.getsockname()[1]
        config = uvicorn.Config(app, lifespan='off', access_log=False, log_level='error',
                                ssl_certfile=str(certificate), ssl_keyfile=str(key))
        instance = uvicorn.Server(config)
        thread = Thread(target=instance.run, kwargs={'sockets': [listener]}, daemon=True)
        thread.start()
        try:
            deadline = time.monotonic() + 10
            while not instance.started:
                if not thread.is_alive() or time.monotonic() > deadline:
                    raise RuntimeError('native_wire_fixture_did_not_start')
                time.sleep(.02)
            yield f'https://localhost:{port}'
        finally:
            instance.should_exit = True
            thread.join(timeout=10)
            if thread.is_alive():
                raise RuntimeError('native_wire_fixture_did_not_stop')


@contextmanager
def native_wire(control, owners, initial, postgres, private):
    """Compose actual production classes without inventing production owner authority."""
    private.mkdir(mode=0o700)
    key, certificate = private / 'key.pem', private / 'certificate.pem'
    subprocess.run(['openssl', 'req', '-x509', '-newkey', 'rsa:2048', '-nodes',
                    '-keyout', str(key), '-out', str(certificate), '-days', '1',
                    '-subj', '/CN=localhost', '-addext', 'subjectAltName=DNS:localhost'],
                   capture_output=True, check=True)
    key.chmod(0o600)
    tokens = {name: secrets.token_urlsafe(48) for name in ('effect', 'boundary')}
    for name, token in tokens.items():
        path = private / name
        path.write_text(token)
        path.chmod(0o600)
    with psycopg.connect(**postgres, autocommit=True) as admin:
        admin.execute('CREATE ROLE native_owner NOLOGIN')
        admin.execute('CREATE ROLE native_runtime LOGIN')
        admin.execute('CREATE DATABASE p07_worker OWNER native_owner')
    worker_settings = postgres | {'dbname': 'p07_worker', 'user': 'native_runtime'}
    with psycopg.connect(**(postgres | {'dbname': 'p07_worker'})) as admin:
        admin.execute('SET ROLE native_owner')
        admin.execute((ROOT / 'workers/lifecycle/migrations/native/001_attempts.sql').read_text())

    def connect():
        return psycopg.connect(**worker_settings, row_factory=dict_row)

    calls = {'effect': 0, 'boundary': 0, 'applies': []}

    def caller(name):
        def resolve(token):
            if not secrets.compare_digest(token, tokens[name]):
                if name == 'boundary':
                    raise Rejected('fixture_caller_denied', 403)
                raise NativeHeld('fixture_caller_denied')
            calls[name] += 1
            return initial['scope']['tenant_id'], initial['executor_id']
        return resolve

    class Tool:
        def inspect(self, binding):
            return {'bundle_sha256': binding.bundle_sha256, 'fixture': 'synthetic_tool'}

        def apply(self, binding, heartbeat):
            with connect() as database:
                rows = database.execute('SELECT kind FROM native.events WHERE operation_id=%s ORDER BY sequence',
                                        (binding.operation_id,)).fetchall()
                assert [row['kind'] for row in rows] == ['prepared', 'apply_started']
            calls['applies'].append(binding.operation_id)
            heartbeat()
            return ProcessResult(0, False)

        def state(self, binding):
            return {'fixture': 'synthetic_native_state'}

    class Observer:
        def observe(self, binding, state):
            return {'binding_sha256': binding.fingerprint, 'independent': True,
                    'observed_at': owners.now, 'outcome': 'observed_present',
                    'fixture': 'synthetic_native_observation'}

    class Tooling:
        def resolve(self, binding):
            return Tool(), Observer()

    with ExitStack() as stack:
        boundary_origin = stack.enter_context(server(NativeBoundaryApp(control, caller('boundary')), certificate, key))
        authority = LifecycleNativeBoundary(NativeEndpoint(boundary_origin, '127.0.0.1', certificate, private / 'boundary'))
        effect = NativeSavedPlanEffect(authority, PostgresNativeJournal(connect), Tooling(), lambda: owners.now)
        effect_origin = stack.enter_context(server(NativeEffectApp(effect, caller('effect')), certificate, key))
        transport = NativeWorkerEffects({initial['executor_id']: NativeWorkerEndpoint(
            effect_origin, '127.0.0.1', certificate, private / 'effect')})
        yield transport, calls, connect
