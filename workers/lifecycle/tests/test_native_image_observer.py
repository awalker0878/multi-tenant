"""Readback repairs only missing custody; ambiguous capture evidence stays held."""

from typing import Any

import pytest
from test_ahv_source import source as source
from test_native import binding as binding
from test_native_http import native_tls as native_tls

from lifecycle_worker.application.native import NativeBinding, NativeHeld
from lifecycle_worker.infrastructure.ahv_source_images import AhvCapturedImages
from lifecycle_worker.infrastructure.native_image_observer import CapturedImageObserver


@pytest.mark.parametrize("ambiguous", [False, True])
def test_capture_observer_recovers_only_absent_receipt_without_native_writes(
    source: dict[str, Any],
    native_tls: Any,
    ambiguous: bool,
) -> None:
    from uuid import uuid4

    c = source
    c["adapter"].execute(c["binding"], lambda: None)
    capture = next(f for e, f in c["journal"].events if e == "source_capture_bound")
    c["journal"].events = [(e, f) for e, f in c["journal"].events if e != "source_capture_bound"]
    if ambiguous:
        c["journal"].events.extend([("source_capture_bound", capture)] * 2)

    class Custody:
        def capture(self, bound: NativeBinding, plan_sha256: str) -> dict[str, Any]:
            assert bound == c["binding"] and plan_sha256 == bound.operation_plan_sha256
            rows = [f for e, f in c["journal"].events if e == "source_capture_bound"]
            if not rows:
                raise NativeHeld("migration_capture_receipt_missing")
            if len(rows) != 1:
                raise NativeHeld("migration_capture_receipt_ambiguous")
            return dict(rows[0])

    read = AhvCapturedImages(c["peer"], native_tls[0].endpoints["compute"])
    calls = []

    def recover(bound: NativeBinding) -> dict[str, Any]:
        calls.append(bound)
        return read.reconcile_capture(bound, c["plan"], c["journal"], lambda: None)

    observer = CapturedImageObserver(
        read,
        c["plan"],
        Custody(),
        c["journal"],
        str(uuid4()),
        str(uuid4()),
        lambda: 100,
        capture_recovery=recover,
    )
    before = len(c["peer"].posts)
    if ambiguous:
        with pytest.raises(NativeHeld, match="ambiguous"):
            observer.observe(c["binding"], c["journal"].resources(c["binding"]))
        assert not calls
    else:
        for _ in range(2):
            result = observer.observe(c["binding"], c["journal"].resources(c["binding"]))
            assert result["outcome"] == "observed_present" and result["application_ready"] is False
        assert len(calls) == 1
    assert len(c["peer"].posts) == before
