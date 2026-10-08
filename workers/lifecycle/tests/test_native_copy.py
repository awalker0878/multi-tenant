"""Real HTTPS export/import with synthetic VM/image data, never native qualification."""

import hashlib
import io
import json
import ssl
import subprocess
import threading
from collections.abc import Iterator
from dataclasses import replace
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest
from test_native import Authority, Journal
from test_native import binding as binding

from lifecycle_worker.application.native import (
    NativeApiExecution,
    NativeBinding,
    NativeHeld,
    digest,
)
from lifecycle_worker.infrastructure.native_copy import (
    GlanceImport,
    GlanceReadback,
    NativeJson,
    NativeVmCopy,
    VmwareExport,
)
from lifecycle_worker.infrastructure.native_http import NativeEndpoint
from lifecycle_worker.infrastructure.openstack_api import NativeWrites


@pytest.fixture
def copy_campaign(binding: NativeBinding, tmp_path: Path) -> Iterator[Any]:
    ca, key = tmp_path / "ca.pem", tmp_path / "key.pem"
    subprocess.run(
        [
            "openssl",
            "req",
            "-x509",
            "-newkey",
            "rsa:2048",
            "-nodes",
            "-keyout",
            str(key),
            "-out",
            str(ca),
            "-days",
            "1",
            "-subj",
            "/CN=native.invalid",
            "-addext",
            "subjectAltName=DNS:native.invalid",
        ],
        check=True,
        capture_output=True,
    )
    writer, reader = str(uuid4()), str(uuid4())
    config = {
        "uuid": str(uuid4()),
        "firmware": "bios",
        "hardware": {
            "device": [{"_typeName": "VirtualDisk", "key": 2000, "capacityInBytes": 1048576}]
        },
    }
    data = b"synthetic-vmdk-stream" * 8000
    fixture: dict[str, Any] = {
        "fault": "",
        "calls": [],
        "images": {},
        "upload_finished": threading.Event(),
        "first_upload_chunk": threading.Event(),
    }

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format: str, *args: Any) -> None:
            pass

        def answer(self, status: int, value: Any = None) -> None:
            if self.path.endswith("/stage") and fixture["fault"] == "stage_rotation":
                (tmp_path / "writer.token").write_text("rotated-after-upload")
            raw = b"" if value is None else json.dumps(value).encode()
            self.send_response(status)
            if value is not None:
                self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            try:
                self.wfile.write(raw)
            except (BrokenPipeError, ConnectionResetError, ssl.SSLEOFError):
                pass

        def record(self) -> bytes:
            fixture["calls"].append(
                {
                    "method": self.command,
                    "path": self.path,
                    "session": self.headers.get("vmware-api-session-id"),
                    "token": self.headers.get("X-Auth-Token"),
                    "range": self.headers.get("Range"),
                    "if_match": self.headers.get("If-Match"),
                }
            )
            length = int(self.headers.get("Content-Length", "0"))
            if self.command != "PUT":
                return self.rfile.read(length)
            received = bytearray()
            while len(received) < length:
                part = self.rfile.read1(min(65536, length - len(received)))
                if not part:
                    break
                received.extend(part)
                if len(received) >= 65536:
                    fixture["first_upload_chunk"].set()
            return bytes(received)

        def do_GET(self) -> None:
            self.record()
            fault = fixture["fault"]
            if self.path == "/identity/auth/tokens":
                self.answer(
                    200,
                    {
                        "token": {
                            "user": {
                                "id": reader
                                if self.headers.get("X-Auth-Token") == "reader"
                                else writer
                            },
                            "project": {
                                "id": str(uuid4()) if fault == "project" else binding.project_id
                            },
                            "expires_at": "2099-01-01T00:00:00Z",
                        }
                    },
                )
            elif self.path.endswith("/runtime"):
                self.answer(
                    200, {"powerState": "poweredOn" if fault == "powered_on" else "poweredOff"}
                )
            elif self.path.endswith("/config"):
                self.answer(200, config | ({"changed": True} if fault == "config" else {}))
            elif self.path.endswith("/state"):
                self.answer(200, "error" if fault == "lease_error" else "ready")
            elif self.path.endswith("/info"):
                self.answer(
                    200,
                    {
                        "entity": {"type": "VirtualMachine", "value": "vm-1"},
                        "leaseTimeout": 60,
                        "deviceUrl": [
                            {
                                "key": "disk-2000",
                                "disk": True,
                                "url": "https://unapproved.invalid/disk"
                                if fault == "url"
                                else origin + "/nfc/disk?ticket=private",
                            }
                        ],
                    },
                )
            elif self.path.startswith("/nfc/"):
                mode = fixture.get("range_fault")
                if mode:
                    offset = int(self.headers.get("Range", "bytes=0-")[6:-1])
                    self.send_response(200 if not offset or mode == "ignored" else 206)
                    self.send_header("Content-Length", str(len(data) - offset))
                    self.send_header("Accept-Ranges", "bytes")
                    if mode != "no_validator":
                        self.send_header(
                            "ETag",
                            'W/"v1"'
                            if mode == "weak"
                            else '"v2"'
                            if offset and mode == "changed"
                            else '"v1"',
                        )
                    if offset:
                        self.send_header(
                            "Content-Range",
                            f"bytes {offset + (1 if mode == 'wrong_range' else 0)}-"
                            f"{len(data) - 1}/{len(data)}",
                        )
                    self.end_headers()
                    part = (
                        data[offset : offset + 32768]
                        if mode == "repeated"
                        else data[:65536]
                        if not offset
                        else data[offset:]
                    )
                    self.wfile.write(part)
                    self.wfile.flush()
                    self.close_connection = True
                    return
                self.send_response(302 if fault == "redirect" else 200)
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
            elif self.path == "/v2/schemas/image":
                self.answer(
                    200,
                    {
                        "properties": {
                            "disk_format": {
                                "enum": ["raw"]
                                if fault == "format"
                                else fixture.get("formats", ["vmdk"])
                            },
                            "container_format": {"enum": ["bare"]},
                        }
                    },
                )
            elif self.path == "/v2/info/import":
                self.answer(
                    200,
                    {
                        "import-methods": {
                            "value": ["web-download"] if fault == "method" else ["glance-direct"]
                        }
                    },
                )
            elif self.path.startswith("/v2/images/"):
                self.answer(200, fixture["images"][self.path.rsplit("/", 1)[-1]])
            else:
                self.answer(404)

        def do_POST(self) -> None:
            raw = self.record()
            fault = fixture["fault"]
            if self.path.endswith("/ExportVm"):
                if fault == "lost_export":
                    self.connection.close()
                    return
                self.answer(200, {"type": "HttpNfcLease", "value": "lease-1"})
            elif self.path.endswith("/HttpNfcLeaseGetManifest"):
                self.answer(
                    200,
                    [
                        {
                            "key": "disk-2000",
                            "disk": True,
                            "size": len(data),
                            "capacity": 1048576,
                            "checksumType": "sha256",
                            "checksum": "0" * 64
                            if fault == "checksum"
                            else hashlib.sha256(data).hexdigest(),
                        }
                    ],
                )
            elif self.path.endswith("/CreateDescriptor"):
                files = json.loads(raw)["cdp"]["ovfFiles"]
                from xml.sax.saxutils import quoteattr

                references = "".join(
                    f'<File ovf:id="f{i}" ovf:href={quoteattr(f["path"])} ovf:size="{f["size"]}"/>'
                    for i, f in enumerate(files)
                )
                disks = "".join(
                    f'<Disk ovf:diskId="d{i}" ovf:fileRef="f{i}" ovf:capacity="{f["capacity"]}"/>'
                    for i, f in enumerate(files)
                )
                self.answer(
                    200,
                    {
                        "ovfDescriptor": '<Envelope xmlns="http://schemas.dmtf.org/ovf/envelope/1" '
                        'xmlns:ovf="http://schemas.dmtf.org/ovf/envelope/1"><References>'
                        + references
                        + "</References><DiskSection>"
                        + disks
                        + "</DiskSection></Envelope>",
                        "error": [],
                        "warning": [],
                    },
                )
            elif self.path.endswith(("/HttpNfcLeaseProgress", "/HttpNfcLeaseComplete")):
                self.answer(200)
            elif self.path == "/v2/images":
                image = json.loads(raw)
                image.update(owner=binding.project_id, status="queued")
                fixture["images"][image["id"]] = image
                if fault == "lost_image":
                    self.connection.close()
                    return
                self.answer(201, image)
            elif self.path.endswith("/import"):
                assert json.loads(raw) == {"method": {"name": "glance-direct"}}
                image = fixture["images"][self.path.split("/")[-2]]
                image.update(
                    status="active",
                    size=len(data),
                    os_hash_algo="sha512",
                    os_hash_value=hashlib.sha512(data).hexdigest(),
                    disk_format="raw" if fault == "converted" else image["disk_format"],
                )
                self.answer(202)
            else:
                self.answer(404)

        def do_PUT(self) -> None:
            received = self.record()
            fixture["upload_bytes"] = len(received)
            fixture["upload_finished"].set()
            assert received == data or (
                fixture.get("allow_partial_upload") and data.startswith(received)
            )
            assert self.path.endswith("/stage")
            try:
                self.answer(500 if fixture["fault"] == "stage" else 204)
            except (BrokenPipeError, ConnectionResetError, ssl.SSLEOFError):
                pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(ca, key)
    server.socket = context.wrap_socket(server.socket, server_side=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    origin = f"https://native.invalid:{server.server_port}"
    plan = {
        "schema_version": 1,
        "method": "native_api_export_import",
        **{
            key: binding.document()[key]
            for key in ("project_id", "ownership_digest", "custody_id", "custody_generation")
        },
        "source": {"vm_id": "vm-1", "api_version": "9.1.1.0", "config_sha256": digest(config)},
        "max_seconds": 10,
        "disks": [
            {
                "key": "disk-2000",
                "capacity": 1048576,
                "max_bytes": 1048576,
                "image_id": str(uuid4()),
                "name": "copied-boot",
                "hw_firmware_type": "bios",
                "hw_disk_bus": "virtio",
            }
        ],
    }
    bound = replace(binding, operation_plan_sha256=digest(plan))
    plan_file = tmp_path / "plan.json"
    plan_file.write_text(json.dumps(plan))
    spool = tmp_path / "spool"
    spool.mkdir(mode=0o700)

    def endpoint(token: str, prefix: str = "") -> NativeEndpoint:
        token_file = tmp_path / (token + ".token")
        token_file.write_text(token)
        return NativeEndpoint(origin + prefix, "127.0.0.1", ca, token_file)

    def glance(token: str, user: str) -> GlanceImport:
        scope = NativeWrites(
            {
                key: endpoint(token, "/identity" if key == "identity" else "/" + key)
                for key in ("identity", "compute", "network", "volume")
            },
            user,
            lambda: 100,
        )
        return GlanceImport(NativeJson(endpoint(token), "X-Auth-Token"), scope)

    source = VmwareExport(
        NativeJson(endpoint("vm-session"), "vmware-api-session-id"), {origin: endpoint("unused")}
    )
    journal = Journal()
    adapter = NativeVmCopy(plan_file, source, glance("writer", writer), journal, spool)
    observer = GlanceReadback(glance("reader", reader), plan, journal, writer, lambda: 100)
    execution = NativeApiExecution(Authority(), journal, adapter, observer, lambda: 100)
    try:
        yield bound, execution, fixture, journal
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)


def test_export_import_integrity_and_independent_readback(copy_campaign: Any) -> None:
    bound, execution, fixture, journal = copy_campaign
    result = execution.execute(bound)
    assert result["observation"]["outcome"] == "observed_present"
    assert result["application_ready"] is False
    calls = fixture["calls"]
    assert sum(row["path"].endswith("/ExportVm") for row in calls) == 1
    assert sum(row["path"].endswith("/stage") for row in calls) == 1
    assert any(row["path"].endswith("/HttpNfcLeaseProgress") for row in calls)
    assert all(
        row["session"] is None and row["token"] is None
        for row in calls
        if row["path"].startswith("/nfc/")
    )
    assert calls[-1]["token"] == "reader"
    assert "private" not in json.dumps(journal.events)
    count = len(calls)
    with pytest.raises(NativeHeld):
        execution.execute(bound)
    assert len(fixture["calls"]) == count


def test_tls_export_continues_exact_bytes_with_current_authority(copy_campaign: Any) -> None:
    _, execution, fixture, _ = copy_campaign
    source = execution.adapter.source
    fixture["range_fault"] = "continue"
    sink = io.BytesIO()
    observations: list[dict[str, Any]] = []
    url = next(iter(source.nfc_endpoints)) + "/nfc/disk?ticket=private"
    heartbeats = 0

    def current() -> None:
        nonlocal heartbeats
        heartbeats += 1

    result = source.download(
        url,
        1048576,
        sink,
        current,
        allow_range_continuation=True,
        on_continuation=observations.append,
    )
    payload = b"synthetic-vmdk-stream" * 8000
    assert sink.read() == payload
    assert result["sha256"] == hashlib.sha256(payload).hexdigest()
    assert len(fixture["calls"]) == 2 and heartbeats > 2
    assert fixture["calls"][1]["range"] == "bytes=65536-"
    assert fixture["calls"][1]["if_match"] == '"v1"'
    assert all(call["session"] is call["token"] is None for call in fixture["calls"])
    assert observations == [
        {
            "bytes": 65536,
            "total": len(payload),
            "prefix_sha256": hashlib.sha256(payload[:65536]).hexdigest(),
            "validator_sha256": hashlib.sha256(b'"v1"').hexdigest(),
        }
    ]


@pytest.mark.parametrize(
    "fault",
    [
        "disabled",
        "no_validator",
        "weak",
        "ignored",
        "changed",
        "wrong_range",
        "repeated",
        "revoked",
        "local_io",
        "journal",
    ],
)
def test_export_continuation_holds_on_uncertainty(copy_campaign: Any, fault: str) -> None:
    _, execution, fixture, _ = copy_campaign
    source = execution.adapter.source
    fixture["range_fault"] = fault

    class Sink(io.BytesIO):
        def write(self, value: Any) -> int:
            if fault == "local_io" and self.tell():
                raise OSError("disk unavailable")
            return super().write(value)

    sink = Sink()

    def current() -> None:
        if fault == "revoked" and sink.tell():
            raise NativeHeld("authority_revoked")

    def journal(value: dict[str, Any]) -> None:
        if fault == "journal":
            raise OSError("journal unavailable")

    with pytest.raises(NativeHeld):
        source.download(
            next(iter(source.nfc_endpoints)) + "/nfc/disk",
            1048576,
            sink,
            current,
            allow_range_continuation=fault != "disabled",
            on_continuation=journal,
        )
    assert len(fixture["calls"]) == (
        3 if fault == "repeated" else 2 if fault in {"ignored", "changed", "wrong_range"} else 1
    )
    assert all(call["method"] == "GET" for call in fixture["calls"])


@pytest.mark.parametrize(
    "fault",
    [
        "project",
        "powered_on",
        "config",
        "lease_error",
        "url",
        "redirect",
        "format",
        "method",
        "lost_export",
        "checksum",
        "lost_image",
        "stage",
        "stage_rotation",
        "converted",
    ],
)
def test_copy_holds_without_fallback_or_repeat(copy_campaign: Any, fault: str) -> None:
    bound, execution, fixture, journal = copy_campaign
    fixture["fault"] = fault
    with pytest.raises(NativeHeld, match="reconciliation"):
        execution.execute(bound)
    count = len(fixture["calls"])
    assert journal.events[-1][0] == "outcome_unknown"
    with pytest.raises(NativeHeld, match="reconciliation"):
        execution.execute(bound)
    assert len(fixture["calls"]) == count
    assert not any(row["path"].endswith("/PowerOnVM_Task") for row in fixture["calls"])


@pytest.mark.parametrize("when", ["before_upload", "during_upload", "expiry"])
def test_glance_upload_stops_before_next_chunk_after_credential_change(
    copy_campaign: Any, when: str
) -> None:
    bound, execution, fixture, _ = copy_campaign
    destination = execution.adapter.destination
    payload = b"synthetic-vmdk-stream" * 8000
    stream = io.BytesIO(payload)
    fixture["allow_partial_upload"] = True
    boundaries = 0

    def current() -> None:
        nonlocal boundaries
        boundaries += 1
        if when in {"during_upload", "expiry"} and stream.tell() > 65536:
            # Observe acceptance of the first chunk before revoking. Closing TLS
            # can discard buffered, unacknowledged bytes on different runtimes.
            assert fixture["first_upload_chunk"].wait(3)
        if (when == "before_upload" and boundaries == 3) or (
            when == "during_upload" and stream.tell() > 65536
        ):
            destination.api.endpoint.token_file.write_text("rotated-during-upload")
        elif when == "expiry" and stream.tell() > 65536:
            destination.scope.clock = lambda: 4070908800  # Token expiry, 2099-01-01.

    with pytest.raises(NativeHeld, match="credential_(changed|expired)"):
        destination.stage(
            bound,
            {"image_id": str(uuid4())},
            stream,
            {"size": len(payload), "sha256": hashlib.sha256(payload).hexdigest()},
            current,
        )
    if when != "before_upload":
        assert fixture["upload_finished"].wait(3)
        assert fixture["upload_bytes"] == 65536
    uploads = [row for row in fixture["calls"] if row["method"] == "PUT"]
    assert len(uploads) == (when != "before_upload")
    # The stream can be read ahead by one chunk, but the changed credential never
    # authorizes that chunk or a follow-up import request.
    assert not any(row["path"].endswith("/import") for row in fixture["calls"])


@pytest.mark.parametrize("when", ["before_request", "during_response"])
def test_vmware_session_rotation_holds_export_without_retry(copy_campaign: Any, when: str) -> None:
    _, execution, fixture, _ = copy_campaign
    api = execution.adapter.source.api

    def current() -> None:
        if when == "before_request" or fixture["calls"]:
            api.endpoint.token_file.write_text("rotated-vmware-session")

    with pytest.raises(NativeHeld, match="credential_changed"):
        api.request("POST", "/sdk/vim25/9.1.1.0/VirtualMachine/vm-1/ExportVm", current)
    assert len(fixture["calls"]) == (when != "before_request")
