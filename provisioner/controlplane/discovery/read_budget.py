"""Process-local endpoint read admission for a bounded discovery batch.

This is backpressure, not a credential, native fence, distributed lease or durable
scheduler. A single gate is shared across tenants/native scopes on the selected
organization/site/platform/endpoint. It never refunds a started read's rate slot.
"""
from __future__ import annotations

import math
import time
from collections import deque
from contextlib import contextmanager
from dataclasses import dataclass
from threading import Condition, Event
from typing import Callable, Iterator

from .model import _id
from .native_credentials import NativeReadHeld


class NativeReadAdmissionHeld(NativeReadHeld):
    """Local scheduling refusal; never publish it as native inventory evidence."""


@dataclass(frozen=True, slots=True)
class EndpointReadPolicy:
    organization_id: str
    site_id: str
    platform_family: str
    endpoint_id: str
    max_concurrent: int
    min_interval_ms: int

    def __post_init__(self):
        if (not all(_id(v) for v in (self.organization_id, self.site_id, self.endpoint_id))
                or self.platform_family not in ('vmware', 'nutanix', 'openstack')
                or type(self.max_concurrent) is not int or not 1 <= self.max_concurrent <= 16
                or type(self.min_interval_ms) is not int or not 1 <= self.min_interval_ms <= 15000):
            raise ValueError('An exact endpoint and bounded read limits are required')

    @property
    def key(self) -> tuple[str, str, str, str]:
        return (self.organization_id, self.site_id, self.platform_family, self.endpoint_id)


class NativeReadGate:
    """FIFO concurrency/rate admission held through native socket cleanup.

    Waiting consumes the caller's existing monotonic request deadline. Revoked or
    expired callers are rechecked while queued and immediately after admission.
    Cancelled/failed tickets are removed without blocking later valid readers.
    """
    def __init__(self, policy: EndpointReadPolicy, *, stopped: Event | None = None):
        if not isinstance(policy, EndpointReadPolicy) or stopped is not None and not isinstance(stopped, Event):
            raise TypeError('An endpoint policy and optional stop event are required')
        self.policy = policy
        self._stopped = stopped if stopped is not None else Event()
        self._condition = Condition()
        self._pending = deque()
        self._active = 0
        self._next_start = 0.0

    def check(self) -> None:
        if self._stopped.is_set():
            raise NativeReadAdmissionHeld('Discovery batch stopped')

    def require_scope(self, scope) -> None:
        if self.policy.key != (scope.organization_id, scope.site_id,
                               scope.platform_family, scope.endpoint_id):
            raise NativeReadAdmissionHeld('Read policy differs from the signed campaign endpoint')
        self.check()

    @contextmanager
    def permit(self, deadline: float, authorize: Callable[[], None]) -> Iterator[None]:
        if (type(deadline) not in (int, float) or not math.isfinite(deadline)
                or not callable(authorize)):
            raise NativeReadAdmissionHeld('An exact read deadline and current authority are required')
        ticket = object()
        admitted = False
        with self._condition:
            if len(self._pending) >= 128:
                raise NativeReadAdmissionHeld('Native read waiting queue is full')
            self._pending.append(ticket)
        try:
            while not admitted:
                self.check()
                authorize()  # Independent authority I/O is never under the gate lock.
                self.check()
                with self._condition:
                    now = time.monotonic()
                    if now >= deadline:
                        raise NativeReadAdmissionHeld('Native read admission deadline expired')
                    if (self._pending[0] is ticket and self._active < self.policy.max_concurrent
                            and now >= self._next_start):
                        self._pending.popleft()
                        self._active += 1
                        self._next_start = now + self.policy.min_interval_ms / 1000
                        admitted = True
                        self._condition.notify_all()
                    else:
                        delay = min(0.05, deadline - now)
                        if self._pending[0] is ticket and self._active < self.policy.max_concurrent:
                            delay = min(delay, max(0.001, self._next_start - now))
                        self._condition.wait(delay)
            self.check()
            authorize()
            if time.monotonic() >= deadline:
                raise NativeReadAdmissionHeld('Native read deadline expired after admission')
            yield
        finally:
            with self._condition:
                if admitted:
                    self._active -= 1
                else:
                    self._pending.remove(ticket)
                self._condition.notify_all()
