"""Synthetic Nova/Cinder peers and real pinned TLS byte transfer, not E3 evidence."""

import hashlib
import io
import json
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest
from test_native import Journal
from test_native import binding as binding
from test_native_http import native_tls as native_tls

from lifecycle_worker.application.native import NativeBinding, NativeHeld, digest
from lifecycle_worker.infrastructure.migration_transfer import NativeBlobDownload
from lifecycle_worker.infrastructure.native_image_archive import NativeImageArchive
from lifecycle_worker.infrastructure.native_image_observer import CapturedImageObserver
from lifecycle_worker.infrastructure.native_json import NativeJson
from lifecycle_worker.infrastructure.openstack_api import NativeWrites
from lifecycle_worker.infrastructure.openstack_capture import OpenStackCapture
from lifecycle_worker.infrastructure.openstack_source_contract import configuration


class Authorization(NativeWrites):
    def __init__(self, project: str) -> None:
        self.project = project
        self.user_id = str(uuid4())
        self.subject_token_sha256 = digest("synthetic-token")
        self.credential_expires_at = 200
        self.clock = lambda: 100
        self.identity_check = lambda: None

    def authorize(self, binding: NativeBinding) -> None:
        assert binding.project_id == self.project


class Api(NativeJson):
    def __init__(
        self, server: dict[str, Any], volume: dict[str, Any], binding: NativeBinding
    ) -> None:
        self.server, self.volume, self.binding = server, volume, binding
        self.snapshot, self.copy, self.root_image, self.volume_image = (
            str(uuid4()) for _ in range(4)
        )
        self.calls: list[tuple[str, str, Any]] = []
        self.fault = ""
        self.metadata: dict[str, Any] = {}

    def request(
        self, method: str, path: str, boundary: Any, body: Any = None, expected: int = 200
    ) -> Any:
        boundary()
        self.calls.append((method, path, deepcopy(body)))
        if method == "POST" and self.fault == "lost_response":
            raise NativeHeld("native_api_outcome_unknown")
        if path == "/servers/" + self.server["id"]:
            return {"server": self.server | ({"status": "ACTIVE"} if self.fault == "power" else {})}
        if path == "/volumes/" + self.volume["id"]:
            return {
                "volume": self.volume | ({"multiattach": True} if self.fault == "shared" else {})
            }
        if path == "/snapshots":
            assert expected == 202 and body["snapshot"]["force"] is True
            self.metadata = body["snapshot"]["metadata"]
            return {"snapshot": {"id": self.snapshot}}
        if path == "/snapshots/" + self.snapshot:
            return {
                "snapshot": {
                    "id": self.snapshot,
                    "volume_id": self.volume["id"],
                    "status": "available",
                    "metadata": self.metadata,
                }
            }
        if path == "/volumes":
            assert body["volume"]["snapshot_id"] == self.snapshot and expected == 202
            return {"volume": {"id": self.volume["id"] if self.fault == "alias" else self.copy}}
        if path == "/volumes/" + self.copy:
            return {
                "volume": {
                    "id": self.copy,
                    "snapshot_id": self.snapshot,
                    "status": "available",
                    "metadata": self.metadata,
                    "attachments": [1] if self.fault == "attached_copy" else [],
                    "encrypted": False,
                }
            }
        if path == "/volumes/" + self.copy + "/action":
            assert body["os-volume_upload_image"]["force"] is False and expected == 202
            assert "visibility" not in body["os-volume_upload_image"]  # Cinder 3.0, not 3.1.
            return {"os-volume_upload_image": {"image_id": self.volume_image}}
        if path.startswith("/images/"):
            key = "root" if path.endswith(self.root_image) else "data"
            return {
                "id": path.split("/")[-1],
                "name": "migration-" + self.binding.operation_id + "-" + key,
                "owner": "foreign" if self.fault == "foreign" else self.server["tenant_id"],
                "visibility": "public" if self.fault == "public" else "private",
                "status": "active",
                "disk_format": "raw",
                "container_format": "bare",
                "size": 512,
                "os_hash_algo": "md5" if self.fault == "weak_hash" else "sha256",
                "os_hash_value": "a" * 64,
            }
        raise AssertionError((method, path, body))

    def request_with_headers(
        self, method: str, path: str, boundary: Any, body: Any = None, expected: int = 200
    ) -> Any:
        boundary()
        self.calls.append((method, path, deepcopy(body)))
        if self.fault == "lost_response":
            raise NativeHeld("native_api_outcome_unknown")
        assert expected == 202
        # Even a foreign returned origin is not followed: only a canonical image id is consumed.
        return None, {"location": "https://untrusted.invalid/images/" + self.root_image}


@pytest.fixture
def capture(
    binding: NativeBinding, tmp_path: Path
) -> tuple[NativeBinding, OpenStackCapture, Api, Journal]:
    project, vm, volume_id = (str(uuid4()) for _ in range(3))
    server: dict[str, Any] = {
        "id": vm,
        "tenant_id": project,
        "status": "SHUTOFF",
        "image": {"id": str(uuid4())},
        "flavor": {"id": "small"},
        "os-extended-volumes:volumes_attached": [{"id": volume_id}],
    }
    volume = {
        "id": volume_id,
        "encrypted": False,
        "multiattach": False,
        "status": "in-use",
        "size": 1,
        "attachments": [{"server_id": vm}],
    }
    p = {
        "schema_version": 2,
        "kind": "openstack_capture",
        "method": "VM_COLD_EXPORT",
        "source_project_id": project,
        "source_vm_id": vm,
        "source_profile_sha256": "b" * 64,
        "server_sha256": digest(configuration("server", server)),
        "max_seconds": 3600,
        "disks": [
            {
                "key": "root",
                "volume_id": None,
                "source_sha256": digest({"image_id": server["image"]["id"], "flavor_id": "small"}),
                "virtual_bytes": 1024**3,
            },
            {
                "key": "data",
                "volume_id": volume_id,
                "source_sha256": digest(configuration("volume", volume)),
                "virtual_bytes": 1024**3,
            },
        ],
    }
    path = tmp_path / "plan.json"
    path.write_text(json.dumps(p))
    bound = replace(binding, operation_plan_sha256=digest(p))
    api, journal = Api(server, volume, bound), Journal()
    journal.claim(bound)
    return (
        bound,
        OpenStackCapture(path, api, api, api, Authorization(project), journal, interval=0),
        api,
        journal,
    )


def test_cold_capture_includes_root_and_every_volume_without_uploading_production_volume(
    capture: Any,
) -> None:
    b, adapter, api, journal = capture
    original = deepcopy(api.server), deepcopy(api.volume)
    adapter.execute(b, lambda: None)
    receipt = journal.events[-1][1]
    assert journal.events[-1][0] == "source_capture_bound"
    assert set(receipt["disks"]) == {"root", "data"}
    assert receipt["consistency"] == "cold_powered_off"
    assert receipt["server_sha256"] == digest(configuration("server", api.server))
    assert (api.server, api.volume) == original
    assert ("POST", "/volumes/" + api.volume["id"] + "/action") not in [
        (m, p) for m, p, _ in api.calls
    ]
    assert len(receipt["owned_objects"]) == 4


@pytest.mark.parametrize(
    "fault",
    [
        "power",
        "shared",
        "alias",
        "attached_copy",
        "foreign",
        "public",
        "weak_hash",
        "lost_response",
    ],
)
def test_capture_failure_retains_partial_receipts_and_never_replays(
    capture: Any, fault: str
) -> None:
    b, adapter, api, journal = capture
    api.fault = fault
    with pytest.raises(NativeHeld):
        adapter.execute(b, lambda: None)
    assert not any(e == "source_capture_bound" for e, _ in journal.events)
    calls = [(m, p) for m, p, _ in api.calls if m == "POST"]
    assert len(calls) == len(set(calls))
    if fault == "attached_copy":
        assert sum(e == "source_object_created" for e, _ in journal.events) == 3


@pytest.mark.parametrize("fault", ["", "size", "digest", "redirect", "encoding"])
def test_pinned_blob_transfer_rejects_unverified_bytes(native_tls: Any, fault: str) -> None:
    reads, peer = native_tls
    data = b"retained native image bytes"
    peer.update(body=data, content_type="application/octet-stream")
    if fault == "redirect":
        peer.update(status=302, location="https://foreign.invalid/bytes")
    if fault == "encoding":
        peer["content_type"] = "text/html"
    expected_size = len(data) + (1 if fault == "size" else 0)
    checksum = hashlib.sha256(data).hexdigest() if fault != "digest" else "a" * 64
    output = io.BytesIO()
    tool = NativeBlobDownload(reads.endpoints["compute"], "X-Auth-Token")
    if fault:
        with pytest.raises(NativeHeld):
            tool.download(
                "/images/image/file", output, expected_size, "sha256", checksum, lambda: None
            )
    else:
        result = tool.download(
            "/images/image/file", output, expected_size, "sha256", checksum, lambda: None
        )
        assert (
            output.getvalue() == data
            and result["sha256"] == checksum
            and result["size"] == len(data)
        )
    assert len(peer["requests"]) == 1


@pytest.mark.parametrize("fault", ["", "mapping", "changed", "interrupted"])
def test_native_archive_keeps_all_disks_and_interrupted_custody(
    binding: NativeBinding, tmp_path: Path, fault: str
) -> None:
    data = b"synthetic raw sectors"
    capture: dict[str, Any] = {
        "source_platform": "openstack",
        "consistency": "cold_powered_off",
        "disks": {"root": {}, "data": {}},
    }
    if fault == "mapping":
        del capture["disks"]["data"]
    p = {
        "schema_version": 2,
        "kind": "native_image_archive",
        "source_platform": "openstack",
        "capture_plan_sha256": "a" * 64,
        "max_seconds": 3600,
        "bytes_per_second": 65536,
        "spool_bytes": 1024,
        "disks": [{"key": k, "max_bytes": 512} for k in ("root", "data")],
    }
    path = tmp_path / "archive.json"
    path.write_text(json.dumps(p))
    b = replace(binding, operation_plan_sha256=digest(p))
    spool = tmp_path / "spool"
    spool.mkdir(mode=0o700)
    journal = Journal()
    journal.claim(b)

    class Source:
        downloaded = False

        def current(self, b: NativeBinding, c: dict[str, Any], boundary: Any) -> None:
            boundary()

        def image(
            self, b: NativeBinding, c: dict[str, Any], key: str, boundary: Any
        ) -> dict[str, Any]:
            return {
                "format": "raw",
                "size": len(data) + (1 if fault == "changed" and self.downloaded else 0),
                "checksum_algorithm": "sha256",
                "checksum": hashlib.sha256(data).hexdigest(),
            }

        def download(self, image: dict[str, Any], sink: Any, boundary: Any) -> dict[str, Any]:
            sink.write(data)
            self.downloaded = True
            if fault == "interrupted":
                raise NativeHeld("transfer_interrupted")
            return {"size": len(data), "sha256": hashlib.sha256(data).hexdigest()}

        def capture(self, b: NativeBinding, plan_sha256: str) -> dict[str, Any]:
            assert plan_sha256 == p["capture_plan_sha256"]
            return capture

    source = Source()
    tool = NativeImageArchive(path, source, journal, source, spool)
    if fault:
        with pytest.raises(NativeHeld):
            tool.execute(b, lambda: None)
        assert not any(e == "export_complete" for e, _ in journal.events)
        if fault != "mapping":
            assert (spool / b.operation_id / "root.raw").read_bytes() == data
    else:
        tool.execute(b, lambda: None)
        assert {f["resource_key"] for e, f in journal.events if e == "disk_transferred"} == {
            "root",
            "data",
        }
        assert journal.events[-1][0] == "export_complete"
        # Keystone principals may use compact 32-character native IDs, even
        # though the worker's own identities use canonical UUID strings.
        observer = CapturedImageObserver(
            source, p, source, journal, "a" * 32, "b" * 32, lambda: 100
        )
        assert observer.observe(b, {})["outcome"] == "observed_present"
        with pytest.raises(NativeHeld, match="independent_native_identity_required"):
            CapturedImageObserver(source, p, source, journal, "a" * 32, "a" * 32, lambda: 100)
        with pytest.raises(NativeHeld, match="invalid_native_identity"):
            CapturedImageObserver(source, p, source, journal, "a" * 32, "invalid", lambda: 100)
        with pytest.raises(FileExistsError):
            tool.execute(b, lambda: None)


@pytest.mark.parametrize(
    "fault", ["", "ignored_range", "wrong_range", "corrupt_prefix", "corrupt_suffix"]
)
def test_continued_native_range_must_prove_the_complete_original_image(
    native_tls: Any, fault: str
) -> None:
    reads, peer = native_tls
    original = b"immutable original image data"
    prefix = original[:10] if fault != "corrupt_prefix" else b"corruption"
    suffix = original[10:] if fault != "corrupt_suffix" else b"x" * (len(original) - 10)
    content_range = f"bytes 10-{len(original) - 1}/{len(original)}"
    peer.update(
        status=200 if fault == "ignored_range" else 206,
        body=suffix,
        content_type="application/octet-stream",
        headers={
            "Content-Range": ["bytes 0-9/10" if fault == "wrong_range" else content_range],
            "Content-Length": [str(len(suffix))],
        },
    )
    tool = NativeBlobDownload(reads.endpoints["compute"], "X-Auth-Token")
    output = io.BytesIO()

    def download() -> dict[str, Any]:
        return tool.download(
            "/images/immutable/file",
            output,
            len(original),
            "sha256",
            hashlib.sha256(original).hexdigest(),
            lambda: None,
            io.BytesIO(prefix),
        )

    if fault:
        with pytest.raises(NativeHeld):
            download()
    else:
        result = download()
        assert prefix + output.getvalue() == original
        assert result["sha256"] == hashlib.sha256(original).hexdigest()
    assert peer["requests"][0]["range"] == "bytes=10-"
