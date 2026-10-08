"""AHV source API peers: complete disk custody, interruption and denied scope."""

import copy
import hashlib
import json
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest
from test_ahv_destination import Journal, Peer, uid
from test_native import binding as binding
from test_native_http import native_tls as native_tls
from test_platform_http import platform_peer as platform_peer

from lifecycle_worker.application.native import NativeBinding, NativeHeld, digest
from lifecycle_worker.infrastructure.ahv_capture import AhvCapture
from lifecycle_worker.infrastructure.ahv_http import COLLECTIONS, AhvHttp
from lifecycle_worker.infrastructure.ahv_source_contract import configuration
from lifecycle_worker.infrastructure.ahv_source_images import AhvCapturedImages
from lifecycle_worker.infrastructure.ahv_tasks import completed, task_identity
from lifecycle_worker.infrastructure.native_http import NativeEndpoint
from lifecycle_worker.infrastructure.native_image_observer import CapturedImageObserver


class SourcePeer(Peer):
    def call(
        self, method: str, path: str, body: Any, headers: dict[str, str], boundary: Any
    ) -> dict[str, Any]:
        result = super().call(method, path, body, headers, boundary)
        if method == "POST":
            old_task = result["document"]["data"]["extId"]
            new_task = "ZXJnb24=:" + old_task.split(":", 1)[1]
            row = self.objects.pop("/api/prism/v4.3/config/tasks/" + old_task)
            row["extId"] = new_task
            self.objects["/api/prism/v4.3/config/tasks/" + new_task] = row
            result["document"]["data"]["extId"] = new_task
            for key, row in self.objects.items():
                if key.startswith(COLLECTIONS["image"]):
                    row["checksum"] = {
                        "$objectType": "vmm.v4.content.ImageSha256Checksum",
                        "hexDigest": "a" * 64,
                    }
        return result


@pytest.fixture
def source(binding: NativeBinding, tmp_path: Path) -> dict[str, Any]:
    vm: dict[str, Any] = {
        "extId": uid(),
        "powerState": "OFF",
        "projectExtId": uid(),
        "cluster": {"extId": uid()},
        "biosUuid": uid(),
        "generationUuid": uid(),
        "disks": [
            {
                "extId": uid(),
                "backingInfo": {"$objectType": "vmm.v4.ahv.config.VmDisk", "diskSizeBytes": 1024},
            }
            for _ in range(2)
        ],
    }
    p: dict[str, Any] = {
        "schema_version": 2,
        "kind": "ahv_capture",
        "method": "VM_COLD_EXPORT",
        "source_project_id": vm["projectExtId"],
        "source_vm_id": vm["extId"],
        "cluster_id": vm["cluster"]["extId"],
        "source_profile_sha256": "b" * 64,
        "vm_sha256": digest(configuration("vm", vm)),
        "max_seconds": 10,
        "disks": [
            {
                "key": "disk-" + str(i),
                "disk_id": d["extId"],
                "source_sha256": digest(d),
                "virtual_bytes": 1024,
                "export_format": "raw",
            }
            for i, d in enumerate(vm["disks"])
        ],
    }
    b = replace(binding, operation_plan_sha256=digest(p))
    file = tmp_path / "capture.json"
    file.write_text(json.dumps(p))
    file.chmod(0o600)
    journal, peer = Journal(), SourcePeer({"project_id": p["source_project_id"]})
    peer.objects[COLLECTIONS["server"] + "/" + vm["extId"]] = vm
    return {
        "binding": b,
        "plan": p,
        "file": file,
        "journal": journal,
        "peer": peer,
        "vm": vm,
        "adapter": AhvCapture(file, peer, journal, interval=0),
    }


def test_all_disks_captured_without_source_mutation_and_separate_readback(
    source: dict[str, Any], native_tls: Any
) -> None:
    c = source
    before = copy.deepcopy(c["vm"])
    c["adapter"].execute(c["binding"], lambda: None)
    assert c["vm"] == before
    assert len(c["peer"].posts) == 2
    assert all(p["path"] == COLLECTIONS["image"] for p in c["peer"].posts)
    assert all(p["body"]["source"]["vmExtId"] == before["extId"] for p in c["peer"].posts)
    capture = next(f for e, f in c["journal"].events if e == "source_capture_bound")

    class Custody:
        def capture(self, binding: NativeBinding, plan_sha256: str) -> dict[str, Any]:
            assert binding == c["binding"] and plan_sha256 == digest(c["plan"])
            return dict(capture)

    reader = AhvCapturedImages(c["peer"], native_tls[0].endpoints["compute"])
    observer = CapturedImageObserver(
        reader, c["plan"], Custody(), c["journal"], uid(), uid(), lambda: 100
    )
    result = observer.observe(c["binding"], c["journal"].resources(c["binding"]))
    assert result["outcome"] == "observed_present" and result["application_ready"] is False
    with pytest.raises(NativeHeld, match="reconciliation"):
        c["adapter"].execute(c["binding"], lambda: None)
    assert len(c["peer"].posts) == 2


@pytest.mark.parametrize(
    "fault", ["running", "foreign", "missing_disk", "shared_disk", "device", "changed"]
)
def test_source_drift_or_unsupported_devices_prevent_posts(
    source: dict[str, Any], fault: str
) -> None:
    c = source
    if fault == "running":
        c["vm"]["powerState"] = "ON"
    if fault == "foreign":
        c["vm"]["projectExtId"] = uid()
    if fault == "missing_disk":
        c["vm"]["disks"].pop()
    if fault == "shared_disk":
        c["vm"]["disks"][0]["backingInfo"]["$objectType"] = (
            "vmm.v4.ahv.config.ADSFVolumeGroupReference"
        )
    if fault == "device":
        c["vm"]["vtpmConfig"] = {"isVtpmEnabled": True}
    if fault == "changed":
        c["vm"]["biosUuid"] = uid()
    with pytest.raises(NativeHeld):
        c["adapter"].execute(c["binding"], lambda: None)
    assert not c["peer"].posts


@pytest.mark.parametrize("fault,accepted", [("lost_response", False), ("task_read", True)])
def test_uncertain_source_capture_retains_exact_task_without_replay(
    source: dict[str, Any], fault: str, accepted: bool
) -> None:
    c = source
    c["peer"].fault = fault
    with pytest.raises(NativeHeld):
        c["adapter"].execute(c["binding"], lambda: None)
    assert len(c["peer"].posts) == 1
    assert bool(c["journal"].ahv_tasks(c["binding"])) is accepted
    assert not any(e == "source_capture_bound" for e, _ in c["journal"].events)


def test_source_image_download_uses_pinned_file_endpoint(native_tls: Any) -> None:
    reads, wire = native_tls
    endpoint = reads.endpoints["compute"]
    # NativeBlobDownload is shared with OpenStack; this verifies the AHV path and digest.
    import io

    image_id = uid()
    data = b"disk data" * 1024
    wire.update(body=data, content_type="application/octet-stream")
    source = AhvCapturedImages(SourcePeer({}), endpoint)
    sink = io.BytesIO()
    result = source.download(
        {
            "image_id": image_id,
            "size": len(data),
            "checksum_algorithm": "sha256",
            "checksum": hashlib.sha256(data).hexdigest(),
        },
        sink,
        lambda: None,
    )
    assert sink.getvalue() == data and result["size"] == len(data)
    assert wire["requests"][0]["path"].endswith(COLLECTIONS["image"] + "/" + image_id + "/file")


@pytest.mark.parametrize("fault", ["vm", "disk", "size", "scope", "shared", "checksum"])
def test_source_image_readback_retains_disk_provenance_and_integrity(
    source: dict[str, Any], native_tls: Any, fault: str
) -> None:
    c = source
    c["adapter"].execute(c["binding"], lambda: None)
    capture = next(f for e, f in c["journal"].events if e == "source_capture_bound")
    key = c["plan"]["disks"][0]["key"]
    row = c["peer"].objects[COLLECTIONS["image"] + "/" + capture["disks"][key]["image_id"]]
    if fault == "vm":
        row["source"]["vmExtId"] = uid()
    elif fault == "disk":
        row["source"]["extId"] = uid()
    elif fault == "size":
        row["sizeBytes"] = 2048
    elif fault == "scope":
        row["projectExtId"] = uid()
    elif fault == "shared":
        row["isSharedWithAllProjects"] = True
    else:
        row["checksum"]["hexDigest"] = "b" * 64
    reader = AhvCapturedImages(c["peer"], native_tls[0].endpoints["compute"])
    with pytest.raises(NativeHeld):
        reader.image(c["binding"], capture, key, lambda: None)


@pytest.mark.parametrize("field", ["errorMessages", "legacyErrorMessage", "warnings"])
def test_success_task_with_diagnostics_never_qualifies(source: dict[str, Any], field: str) -> None:
    c = source
    c["adapter"].execute(c["binding"], lambda: None)
    task = next(iter(c["journal"].ahv_tasks(c["binding"]).values()))
    c["peer"].objects["/api/prism/v4.3/config/tasks/" + task["task_id"]][field] = ["warning"]
    with pytest.raises(NativeHeld, match="failed_or_unknown"):
        completed(c["peer"], task, lambda: None)


def test_source_power_change_between_disks_preserves_partial_custody(
    source: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    c = source
    original = c["peer"].call

    def changed(method: str, path: str, body: Any, headers: dict[str, str], boundary: Any) -> Any:
        result = original(method, path, body, headers, boundary)
        if method == "POST":
            c["vm"]["powerState"] = "ON"
        return result

    monkeypatch.setattr(c["peer"], "call", changed)
    with pytest.raises(NativeHeld, match="source_not_stopped"):
        c["adapter"].execute(c["binding"], lambda: None)
    assert len(c["peer"].posts) == 1
    assert len(c["journal"].resources(c["binding"])) == 1
    assert not any(event == "source_capture_bound" for event, _ in c["journal"].events)


@pytest.mark.parametrize("prefix", ["ZXJnb24=", "a/b+c=="])
def test_real_task_identifiers_are_preserved_and_encoded_on_tls_wire(
    platform_peer: tuple[NativeEndpoint, dict[str, Any]], prefix: str
) -> None:
    from urllib.parse import quote

    endpoint, wire = platform_peer
    task_id, image_id = prefix + ":" + uid(), uid()
    wire.update(
        status=200,
        body=json.dumps(
            {
                "data": {
                    "extId": task_id,
                    "status": "SUCCEEDED",
                    "entitiesAffected": [{"extId": image_id}],
                }
            }
        ).encode(),
    )
    assert completed(AhvHttp(endpoint), {"task_id": task_id}, lambda: None) == image_id
    assert wire["requests"][0]["path"].endswith(quote(task_id, safe=":="))


@pytest.mark.parametrize("value", ["task", "../task", "ergon:bad", "x:" + uid() + "?unsafe=1"])
def test_task_identity_rejects_non_native_or_route_injected_ids(value: str) -> None:
    with pytest.raises(NativeHeld, match="task_identity"):
        task_identity(value)


@pytest.mark.parametrize("fault", ["last_poll", "receipt_write"])
def test_read_only_reconciliation_recovers_complete_capture_after_interruption(
    source: dict[str, Any], native_tls: Any, monkeypatch: pytest.MonkeyPatch, fault: str
) -> None:
    c = source
    original_call, original_record = c["peer"].call, c["journal"].record

    def interrupted_call(
        method: str, path: str, body: Any, headers: dict[str, str], boundary: Any
    ) -> Any:
        if fault == "last_poll" and "/tasks/" in path and len(c["peer"].posts) == 2:
            raise NativeHeld("poll_interrupted")
        return original_call(method, path, body, headers, boundary)

    def interrupted_record(b: NativeBinding, event: str, facts: dict[str, Any]) -> None:
        if fault == "receipt_write" and event == "source_capture_bound":
            raise NativeHeld("receipt_interrupted")
        original_record(b, event, facts)

    monkeypatch.setattr(c["peer"], "call", interrupted_call)
    monkeypatch.setattr(c["journal"], "record", interrupted_record)
    with pytest.raises(NativeHeld, match="interrupted"):
        c["adapter"].execute(c["binding"], lambda: None)
    assert len(c["peer"].posts) == 2
    assert not any(event == "source_capture_bound" for event, _ in c["journal"].events)
    monkeypatch.setattr(c["peer"], "call", original_call)
    monkeypatch.setattr(c["journal"], "record", original_record)
    reader = AhvCapturedImages(c["peer"], native_tls[0].endpoints["compute"])
    receipt = reader.reconcile_capture(c["binding"], c["plan"], c["journal"], lambda: None)
    assert set(receipt["disks"]) == {disk["key"] for disk in c["plan"]["disks"]}
    assert len(c["journal"].resources(c["binding"])) == 2
    assert len(c["peer"].posts) == 2
    assert sum(event == "source_capture_bound" for event, _ in c["journal"].events) == 1


@pytest.mark.parametrize("fault", ["missing_task", "running", "foreign_task", "foreign_image"])
def test_capture_reconciliation_holds_partial_or_changed_state_without_posts(
    source: dict[str, Any], fault: str
) -> None:
    c = source
    c["adapter"].execute(c["binding"], lambda: None)
    c["journal"].events = [
        (event, facts) for event, facts in c["journal"].events if event != "source_capture_bound"
    ]
    if fault == "missing_task":
        c["journal"].events = [
            (event, facts)
            for event, facts in c["journal"].events
            if event != "ahv_task_accepted" or facts["resource_key"] != "disk-1"
        ]
    elif fault == "running":
        c["vm"]["powerState"] = "ON"
    elif fault == "foreign_task":
        for event, facts in c["journal"].events:
            if event == "ahv_task_accepted":
                facts["request_id"] = uid()
                break
    else:
        for path, row in c["peer"].objects.items():
            if path.startswith(COLLECTIONS["image"]):
                row["source"]["vmExtId"] = uid()
                break
    with pytest.raises(NativeHeld):
        c["adapter"].reconcile_capture(c["binding"], lambda: None)
    assert len(c["peer"].posts) == 2
    assert not any(event == "source_capture_bound" for event, _ in c["journal"].events)
