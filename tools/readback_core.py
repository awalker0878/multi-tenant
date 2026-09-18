#!/usr/bin/env python3
"""Bounded GET-only infrastructure observations; never a deployment/authorization engine.

Responses are compared in memory. Reports contain digests, mismatch paths and status
codes, not arbitrary response bodies or service errors. Exact resource scope is an
operator-supplied engineering record, NOT proof of native RBAC or approval.
"""
from __future__ import annotations
import base64
from datetime import datetime, timezone
import hashlib
import http.client
import json
import math
import os
from pathlib import Path
import re
import socket
import ssl
import time
from urllib.parse import urlsplit

LIMIT = 2 * 1024 * 1024
MAX_RESOURCES = 20
ID = re.compile(r'^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$')
HEX = re.compile(r'^[0-9a-f]{64}$')
UUID = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$')
SENSITIVE = re.compile(r'password|secret|credential|authorization|private.?key|token', re.I)


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def timestamp(value: str) -> datetime:
    if not isinstance(value, str) or len(value) > 64:
        raise ValueError('Expected timezone-aware timestamp')
    result = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if result.tzinfo is None:
        raise ValueError('Timezone required')
    return result.astimezone(timezone.utc)


def strict_loads(value: str | bytes):
    def pairs(items):
        result = {}
        for k, v in items:
            if k in result:
                raise ValueError('Duplicate JSON member')
            result[k] = v
        return result
    def reject(_):
        raise ValueError('Non-finite JSON number')
    result = json.loads(value, object_pairs_hook=pairs, parse_constant=reject)
    # JSON 1e999 is accepted by the stdlib as infinity unless checked afterward.
    def walk(item, depth=0):
        if depth > 40:
            raise ValueError('Excessive JSON nesting')
        if isinstance(item, float) and not math.isfinite(item):
            raise ValueError('Non-finite JSON number')
        if isinstance(item, (dict, list)):
            for child in (item.values() if isinstance(item, dict) else item):
                walk(child, depth+1)
    walk(result)
    return result


def load(path: Path):
    with path.open('rb') as stream:
        data = stream.read(LIMIT + 1)
    if len(data) > LIMIT:
        raise ValueError('Input too large')
    return strict_loads(data)


def digest(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def exact_keys(value, required: set[str], optional: set[str] = frozenset()):
    if not isinstance(value, dict) or not required <= value.keys() or value.keys() - required - optional:
        raise ValueError('Missing or unexpected record fields')


def text(value, label='identifier', length=160):
    if not isinstance(value, str) or not value.strip() or len(value) > length or any(ord(c) < 32 or ord(c) == 127 for c in value):
        raise ValueError(f'Invalid {label}')
    return value


def identifier(value):
    if not isinstance(value, str) or not ID.fullmatch(value):
        raise ValueError('Invalid scoped identifier')
    return value


def reject_sensitive(value):
    if isinstance(value, dict):
        for k, v in value.items():
            if SENSITIVE.search(k):
                raise ValueError('Credential-shaped field not permitted')
            reject_sensitive(v)
    elif isinstance(value, list):
        for v in value:
            reject_sensitive(v)
    elif isinstance(value, str):
        if value in ('$UNKNOWN', '$REDACTED') or '-----BEGIN ' in value or len(value) > 4096:
            raise ValueError('Key material or oversized string not permitted')


def origin(value: str) -> str:
    text(value, 'HTTPS origin', 512)
    if any(c.isspace() for c in value) or '\\' in value or '%' in value:
        raise ValueError('Ambiguous origin')
    p = urlsplit(value)
    if p.scheme != 'https' or not p.hostname or p.username is not None or p.password is not None or p.path not in ('', '/') or p.query or p.fragment:
        raise ValueError('An exact HTTPS origin without path or credentials is required')
    port = p.port or 443
    if not 1 <= port <= 65535:
        raise ValueError('Invalid origin port')
    hostname = p.hostname.lower()
    hostpart = f'[{hostname}]' if ':' in hostname else hostname
    return f'https://{hostpart}' + (f':{port}' if port != 443 else '')


def common_manifest(manifest: dict, platform: str):
    exact_keys(manifest, {'platform', 'origin', 'operation_id', 'tenant_id', 'scope_id',
                         'engineering_record_ref', 'target_binding_ref', 'contact_enabled',
                         'resources', 'profile'}, {'task'})
    if manifest['platform'] != platform or type(manifest['contact_enabled']) is not bool:
        raise ValueError('Wrong platform or contact setting')
    if manifest['origin'] != origin(manifest['origin']):
        raise ValueError('Origin must be in canonical form')
    for k in ('operation_id', 'tenant_id', 'scope_id'):
        identifier(manifest[k])
    for k in ('engineering_record_ref', 'target_binding_ref'):
        text(manifest[k], k)
    if not isinstance(manifest['resources'], list) or not 1 <= len(manifest['resources']) <= MAX_RESOURCES:
        raise ValueError('Provide 1-20 exact resources')
    reject_sensitive(manifest)


def differences(actual, expected, path='') -> list[str]:
    """Compare selected dict fields. Lists have exact membership AND order.

    Unknown dictionary fields are outside coverage. Missing expected fields remain
    unknown, never silently defaulted to empty/false. Bool is not the integer 1.
    """
    if type(actual) is not type(expected):
        return [path + ':type']
    if isinstance(expected, dict):
        result = []
        for k, value in expected.items():
            child = path + '/' + k
            result += ([child + ':missing'] if k not in actual else differences(actual[k], value, child))
        return result[:100]
    if isinstance(expected, list):
        if len(actual) != len(expected):
            return [path + ':length']
        return [item for i, (a, e) in enumerate(zip(actual, expected)) for item in differences(a, e, path + '/' + str(i))][:100]
    return [] if actual == expected else [path + ':value']


class ObservationError(Exception):
    """Only constant safe codes are carried, never response text or credentials."""
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


class ReadClient:
    """One HTTPS GET per call; no redirects, cookies, proxies, discovery or writes."""
    def __init__(self, endpoint: str, expected_origin: str, username: str, password: str,
                 allowed_targets: set[str], ca_file: str | None = None,
                 timeout: float = 5.0, budget: float = 60.0):
        self.origin = origin(endpoint)
        if self.origin != origin(expected_origin):
            raise ValueError('Target origin differs from accepted origin')
        p = urlsplit(self.origin)
        self.host, self.port = p.hostname, p.port or 443
        text(username, 'injected username', 256)
        text(password, 'injected password', 4096)
        if ':' in username:
            raise ValueError('Invalid Basic authentication username')
        self._auth = 'Basic ' + base64.b64encode((username + ':' + password).encode()).decode('ascii')
        if not allowed_targets or any(not t.startswith('/') or t.startswith('//') or '\\' in t or '#' in t or any(ord(c)<33 or ord(c)>126 for c in t) for t in allowed_targets):
            raise ValueError('Invalid exact GET targets')
        self.allowed_targets = frozenset(allowed_targets)
        if isinstance(timeout, bool) or isinstance(budget, bool) or not 0.1 <= timeout <= 10 or not 1 <= budget <= 120:
            raise ValueError('Invalid bounded transport settings')
        self.timeout, self.deadline = timeout, time.monotonic()+budget
        self.request_count = 0
        self.context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        self.context.minimum_version = ssl.TLSVersion.TLSv1_2
        self.context.verify_flags |= ssl.VERIFY_X509_STRICT
        if ca_file:
            self.context.load_verify_locations(cafile=ca_file)
        else:
            self.context.load_default_certs()

    def get(self, target: str) -> tuple[dict, str | None]:
        if target not in self.allowed_targets:
            raise ObservationError('TARGET_NOT_IN_ACCEPTED_SCOPE')
        remaining = self.deadline - time.monotonic()
        if remaining <= 0 or self.request_count >= 400:
            raise ObservationError('OBSERVATION_BUDGET_EXHAUSTED')
        self.request_count += 1
        connection = http.client.HTTPSConnection(self.host, self.port, timeout=min(self.timeout, remaining), context=self.context)
        try:
            connection.request('GET', target, headers={'Authorization': self._auth, 'Accept': 'application/json',
                'Accept-Encoding': 'identity', 'Connection': 'close', 'Cache-Control': 'no-cache'})
            read_socket = connection.sock
            response = connection.getresponse()
            if response.status != 200:
                raise ObservationError('HTTP_'+str(response.status))
            if response.getheader('Content-Encoding', 'identity').lower() not in ('', 'identity'):
                raise ObservationError('ENCODED_RESPONSE_REFUSED')
            if response.getheader('Content-Type', '').split(';')[0].strip().lower() != 'application/json':
                raise ObservationError('NON_JSON_RESPONSE')
            sizes = response.headers.get_all('Content-Length', [])
            if len(sizes)>1 or (sizes and (not sizes[0].isdigit() or int(sizes[0])>LIMIT)):
                raise ObservationError('INVALID_RESPONSE_SIZE')
            if response.getheader('Transfer-Encoding') and sizes:
                raise ObservationError('AMBIGUOUS_RESPONSE_FRAMING')
            data = bytearray()
            while True:
                remaining = self.deadline-time.monotonic()
                if remaining<=0:
                    raise ObservationError('OBSERVATION_BUDGET_EXHAUSTED')
                if read_socket and read_socket.fileno() >= 0:
                    read_socket.settimeout(min(self.timeout, remaining))
                # read1 limits each iteration; the absolute budget is checked between reads.
                chunk = response.read1(min(65536, LIMIT+1-len(data)))
                if not chunk:
                    break
                data.extend(chunk)
                if len(data)>LIMIT:
                    raise ObservationError('RESPONSE_TOO_LARGE')
            if sizes and len(data)!=int(sizes[0]):
                raise ObservationError('TRUNCATED_RESPONSE')
            value = strict_loads(bytes(data))
            if not isinstance(value, dict):
                raise ObservationError('OBJECT_RESPONSE_REQUIRED')
            etags = response.headers.get_all('ETag', [])
            if len(etags)>1:
                raise ObservationError('AMBIGUOUS_ETAG')
            etag = etags[0] if etags else None
            if etag is not None:
                text(etag, 'ETag', 512)
                if etag.startswith('W/') or not etag.startswith('"') or not etag.endswith('"'):
                    raise ObservationError('STRONG_ETAG_REQUIRED')
            return value, etag
        except ObservationError:
            raise
        except ssl.SSLCertVerificationError:
            raise ObservationError('TLS_CERTIFICATE_REJECTED') from None
        except (TimeoutError, socket.timeout):
            raise ObservationError('READ_TIMEOUT') from None
        except (OSError, http.client.HTTPException, ValueError, RecursionError):
            raise ObservationError('TRANSPORT_OR_JSON_ERROR') from None
        finally:
            connection.close()


class PrivateJournal:
    """Create a new owner-only evidence file before native reads; never overwrite.

    A crash leaves an incomplete non-accepting record. This is a local file, not an
    immutable evidence store or a signature. Protect its parent directory separately.
    """
    def __init__(self, path: Path):
        self.fd = os.open(path, os.O_CREAT|os.O_EXCL|os.O_WRONLY|getattr(os,'O_NOFOLLOW',0), 0o600)
        self.finished = False
        os.fchmod(self.fd, 0o600)
        self.write({'kind':'NATIVE_READBACK_INCOMPLETE', 'started_at':now(), 'outcome':'HOLD_INCOMPLETE'})

    def write(self, value):
        data = (json.dumps(value, indent=2, allow_nan=False)+'\n').encode()
        os.lseek(self.fd, 0, os.SEEK_SET)
        os.ftruncate(self.fd, 0)
        with os.fdopen(os.dup(self.fd), 'wb') as f:
            f.write(data);f.flush();os.fsync(f.fileno())

    def close(self):
        if not self.finished:
            os.close(self.fd); self.finished = True

    def __enter__(self): return self
    def __exit__(self, *_): self.close()


def outcome(states: list[dict], stable_rounds: int) -> str:
    if not states or any(s.get('progress')=='UNKNOWN' or s.get('config_status')=='UNKNOWN' for s in states):
        return 'HOLD_UNCERTAIN'
    if any(s.get('progress')=='FAILED' for s in states):
        return 'HOLD_NATIVE_FAILURE'
    if any(s.get('progress')=='PENDING' for s in states):
        return 'HOLD_NATIVE_PENDING'
    if any(s.get('config_status')=='DIFFERENT' for s in states):
        return 'HOLD_DIFFERENCE'
    if stable_rounds<2:
        return 'HOLD_UNSTABLE'
    if all(s.get('config_status')=='MATCH' and s.get('progress')=='COMPLETE' for s in states):
        return 'READBACK_MATCH_NOT_QUALIFIED'
    return 'HOLD_UNCERTAIN'


def observe(manifest: dict, client: ReadClient, adapter, rounds=3, interval=0.1) -> dict:
    adapter.validate(manifest)
    if manifest['origin'] != client.origin:
        raise ValueError('Client/manifest origin mismatch')
    if type(rounds) is not int or not 2<=rounds<=10 or isinstance(interval,bool) or not 0<=interval<=10:
        raise ValueError('Bounded observation settings required')
    started = now(); history=[]; stable=0; previous=None
    for i in range(rounds):
        try:
            states=adapter.sample(manifest, client)
            history_check=getattr(adapter,'validate_observation_history',None)
            if history_check is not None:history_check(manifest,history,states)
        except ObservationError as error:
            states=[{'resource_key':'scope', 'config_status':'UNKNOWN', 'progress':'UNKNOWN', 'reason':error.code}]
        snapshot=digest(states)
        stable=stable+1 if snapshot==previous else 1
        previous=snapshot
        current=outcome(states, stable)
        history.append({'round':i+1, 'observed_at':now(), 'snapshot_sha256':snapshot, 'states':states, 'outcome':current})
        if current in ('READBACK_MATCH_NOT_QUALIFIED','HOLD_NATIVE_FAILURE','HOLD_DIFFERENCE','HOLD_UNCERTAIN'):
            break
        if i+1<rounds:
            time.sleep(interval)
    report={'kind':'NATIVE_READBACK_V1','platform':manifest['platform'],'profile':manifest['profile'],
        'origin':client.origin,'operation_id':manifest['operation_id'],'tenant_id':manifest['tenant_id'],
        'scope_id':manifest['scope_id'],'target_binding_ref':manifest['target_binding_ref'],
        'manifest_sha256':digest(manifest),'started_at':started,'completed_at':now(),
        'outcome':current,'stable_rounds':stable,'request_count':client.request_count,'history':history,
        'coverage':'Exact enumerated resources and selected fields; not inventory completeness, RBAC, packet-path or live qualification.',
        'may_apply':False,'may_delete':False,'may_activate':False}
    report['content_sha256']=digest(report)
    return report
