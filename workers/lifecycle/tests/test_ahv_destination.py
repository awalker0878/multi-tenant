"""Synthetic Prism API component tests. They do not establish native AHV support."""

import asyncio
import copy
import hashlib
import json
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest
from test_native import binding as binding
from test_platform_http import platform_peer as platform_peer

from lifecycle_worker.application.native import (
    NativeApiExecution,
    NativeBinding,
    NativeHeld,
    digest,
)
from lifecycle_worker.infrastructure.ahv_destination import AhvDestination, AhvDestinationObserver
from lifecycle_worker.infrastructure.ahv_http import COLLECTIONS, AhvHttp
from lifecycle_worker.infrastructure.ahv_staging import AhvArtifactApp, AhvStaging
from lifecycle_worker.infrastructure.native_http import NativeEndpoint


def uid() -> str:
    return str(uuid4())


class Journal:
    def __init__(self) -> None:
        self.events: list[tuple[str, dict[str, Any]]] = []
        self.claimed = False

    def claim(self, b: NativeBinding) -> bool:
        if self.claimed:
            return False
        self.claimed = True
        return True

    def record(self, b: NativeBinding, event: str, facts: dict[str, Any]) -> None:
        self.events.append((event, copy.deepcopy(facts)))

    def resources(self, b: NativeBinding) -> dict[str, dict[str, str]]:
        return {
            f["resource_key"]: {"kind": f["kind"], "id": f["native_id"]}
            for e, f in self.events
            if e == "request_accepted"
        }

    def transfers(self, b: NativeBinding) -> dict[str, dict[str, Any]]:
        return {f["resource_key"]: f for e, f in self.events if e == "disk_transferred"}

    def ahv_tasks(self, b: NativeBinding) -> dict[str, dict[str, Any]]:
        return {f["resource_key"]: f for e, f in self.events if e == "ahv_task_accepted"}


class Peer:
    def __init__(self, p: dict[str, Any]) -> None:
        self.p = p
        self.objects: dict[str, dict[str, Any]] = {}
        self.posts: list[dict[str, Any]] = []
        self.fault = ""

    def call(
        self,
        method: str,
        path: str,
        body: Any,
        headers: dict[str, str],
        boundary: Callable[[], None],
    ) -> dict[str, Any]:
        boundary()
        if method == "POST":
            self.posts.append({"path": path, "body": copy.deepcopy(body), "headers": headers})
            key = uid()
            task = "ergon:" + uid()
            created = copy.deepcopy(body) | {"extId": key}
            if path == COLLECTIONS["image"]:
                created["sizeBytes"] = 1024
            if path == COLLECTIONS["server"]:
                for device in created["disks"] + created["nics"]:
                    device["extId"] = uid()
            self.objects[path + "/" + key] = created
            self.objects["/api/prism/v4.3/config/tasks/" + task] = {
                "extId": task,
                "status": "SUCCEEDED",
                "entitiesAffected": [{"extId": key}],
            }
            if self.fault == "lost_response":
                raise NativeHeld("response_lost")
            return {"document": {"data": {"extId": task}}, "etag": ""}
        if "/tasks/" in path and self.fault == "task_read":
            raise NativeHeld("task_read_interrupted")
        if path in self.objects:
            return {"document": {"data": copy.deepcopy(self.objects[path])}, "etag": '"one"'}
        key = path.rsplit("/", 1)[1]
        row: dict[str, Any] = {"extId": key, "projectExtId": self.p["project_id"]}
        if "/clusters/" in path:
            row["config"] = {"isAvailable": True, "hypervisorTypes": ["AHV"]}
        if "/storage-containers/" in path:
            row.update(
                clusterExtId=self.p["cluster_id"], isMarkedForRemoval=False, isInternal=False
            )
        if "/policies/" in path:
            row["state"] = "ENFORCE"
        return {"document": {"data": row}, "etag": '"one"'}


@pytest.fixture
def campaign(binding: NativeBinding, tmp_path: Path) -> dict[str, Any]:
    p: dict[str, Any] = {
        "api_versions": dict.fromkeys(
            ("vmm", "prism", "clustermgmt", "networking", "microseg", "iam"), "v4.3"
        ),
        **{
            k: binding.document()[k]
            for k in ("custody_id", "custody_generation", "ownership_digest")
        },
        "schema_version": 1,
        "kind": "ahv_destination",
        "project_id": binding.project_id,
        "prism_central_id": uid(),
        "cluster_id": uid(),
        "destination_sha256": "d" * 64,
        "conversion_plan_sha256": "e" * 64,
        "name": "migration-copy",
        "cpu": 2,
        "memory_bytes": 1073741824,
        "max_seconds": 10,
        "category_ids": [uid()],
        "policy_ids": [uid()],
        "shared_resource_ids": [],
        "disks": [
            {
                "key": "disk-" + str(n),
                "index": n,
                "format": "raw",
                "virtual_bytes": 1024,
                "storage_container_id": uid(),
            }
            for n in range(2)
        ],
        "nics": [
            {"source_key": n, "quarantine_subnet_id": uid(), "production_subnet_id": uid()}
            for n in range(2)
        ],
    }
    b = replace(binding, operation_plan_sha256=digest(p))
    plan = tmp_path / "plan.json"
    plan.write_text(json.dumps(p))
    plan.chmod(0o600)
    spool, grants = tmp_path / "spool", tmp_path / "grants"
    spool.mkdir(mode=0o700)
    grants.mkdir(mode=0o700)
    staging = AhvStaging(grants, spool, "https://artifacts.invalid", lambda: 100)
    data = b"x" * 1024
    receipt = {
        "format": "raw",
        "sector_comparison": "passed",
        "size": len(data),
        "virtual_bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
        "sha512": hashlib.sha512(data).hexdigest(),
    }
    prior = uid()
    for disk in p["disks"]:
        folder = spool / prior / disk["key"]
        folder.mkdir(parents=True)
        (folder / "disk.raw").write_bytes(data)

    class Custody:
        def artifact(self, supplied: NativeBinding, sha: str, kind: str) -> dict[str, Any]:
            assert sha == p["conversion_plan_sha256"] and kind == "conversion"
            return {"operation_id": prior, "disks": {d["key"]: receipt for d in p["disks"]}}

    class Authority:
        def require_current(self, supplied: NativeBinding, boundary: str) -> None:
            assert supplied == b

    journal, peer = Journal(), Peer(p)
    adapter = AhvDestination(plan, peer, journal, Custody(), staging, interval=0)
    observer = AhvDestinationObserver(plan, peer, journal, lambda: 100, uid(), uid(), lambda: None)
    execution = NativeApiExecution(Authority(), journal, adapter, observer, lambda: 100)
    return dict(
        binding=b,
        plan=p,
        peer=peer,
        journal=journal,
        adapter=adapter,
        observer=observer,
        execution=execution,
        staging=staging,
        receipt=receipt,
        disk=spool / prior / p["disks"][0]["key"] / "disk.raw",
    )


def test_all_disk_image_import_vm_mapping_and_independent_observation(
    campaign: dict[str, Any],
) -> None:
    c = campaign
    result = c["execution"].execute(c["binding"])
    assert result["observation"]["outcome"] == "observed_present"
    assert result["activation_authorized"] is False and result["application_ready"] is False
    posts = c["peer"].posts
    assert [r["path"] for r in posts] == [COLLECTIONS["image"]] * 2 + [COLLECTIONS["server"]]
    assert len({r["headers"]["Ntnx-Request-Id"] for r in posts}) == 3
    assert posts[-1]["body"]["powerState"] == "OFF"
    assert all(n["backingInfo"]["isConnected"] is False for n in posts[-1]["body"]["nics"])
    assert not list(c["staging"].root.iterdir())
    assert "https://artifacts" not in json.dumps(c["journal"].events)
    with pytest.raises(NativeHeld, match="reconciliation"):
        c["execution"].execute(c["binding"])
    assert len(posts) == 3


@pytest.mark.parametrize("fault", ["hash", "lost_response", "task_read"])
def test_failure_never_replays_creation_or_claims_success(
    campaign: dict[str, Any], fault: str
) -> None:
    c = campaign
    if fault == "hash":
        c["disk"].write_bytes(b"wrong" * 205)
    else:
        c["peer"].fault = fault
    with pytest.raises(NativeHeld, match="reconciliation"):
        c["execution"].execute(c["binding"])
    count = len(c["peer"].posts)
    assert count == (0 if fault == "hash" else 1)
    c["peer"].fault = ""
    assert c["execution"].reconcile(c["binding"])["outcome"] == "held"
    assert len(c["peer"].posts) == count
    if fault == "task_read":
        assert len(c["journal"].ahv_tasks(c["binding"])) == 1


@pytest.mark.parametrize("fault", ["project", "disk", "nic", "power", "category", "task"])
def test_observer_detects_foreign_or_changed_destination(
    campaign: dict[str, Any], fault: str
) -> None:
    c = campaign
    c["execution"].execute(c["binding"])
    vm = next(
        row for path, row in c["peer"].objects.items() if path.startswith(COLLECTIONS["server"])
    )
    if fault == "project":
        vm["projectExtId"] = uid()
    if fault == "disk":
        vm["disks"].pop()
    if fault == "nic":
        vm["nics"][0]["backingInfo"]["isConnected"] = True
    if fault == "power":
        vm["powerState"] = "ON"
    if fault == "category":
        vm["categories"] = []
    if fault == "task":
        for path, row in c["peer"].objects.items():
            if "/tasks/" in path:
                row["status"] = "FAILED"
    assert c["execution"].reconcile(c["binding"])["outcome"] == "held"


@pytest.mark.parametrize("fault", ["", "expired", "changed", "foreign_ip", "http", "revoked"])
def test_private_https_staging_auth_custody_and_expiry(
    campaign: dict[str, Any], fault: str
) -> None:
    c = campaign
    staging = c["staging"]
    url, token = staging.grant(c["binding"], c["disk"], c["receipt"])
    app = AhvArtifactApp(staging, ["192.0.2.10"])
    if fault == "expired":
        staging.clock = lambda: 201
    if fault == "changed":
        c["disk"].write_bytes(b"f" * 1024)
    if fault == "revoked":
        staging.revoke(token)
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/ahv-artifacts/" + token,
        "scheme": "http" if fault == "http" else "https",
        "query_string": b"",
        "client": ("192.0.2.11" if fault == "foreign_ip" else "192.0.2.10", 1),
    }
    replies: list[dict[str, Any]] = []

    async def send(message: dict[str, Any]) -> None:
        replies.append(message)

    asyncio.run(app(scope, None, send))
    assert replies[0]["status"] == (404 if fault else 200)
    assert url.startswith("https://")
    if not fault:
        assert b"".join(r.get("body", b"") for r in replies) == b"x" * 1024


@pytest.mark.parametrize("status", [202, 301, 403, 409, 429, 500])
def test_actual_tls_import_transport_no_retry(
    platform_peer: tuple[NativeEndpoint, dict[str, Any]], status: int
) -> None:
    endpoint, peer = platform_peer
    peer.update(status=status, body=b'{"data":{"extId":"ergon:task"}}')
    http = AhvHttp(endpoint)
    headers = {"Ntnx-Request-Id": uid()}
    if status == 202:
        http.call("POST", COLLECTIONS["image"], {"name": "copy"}, headers, lambda: None)
        assert peer["requests"][0]["headers"]["X-Ntnx-Api-Key"] == "synthetic-platform-credential"
    else:
        with pytest.raises(NativeHeld):
            http.call("POST", COLLECTIONS["image"], {}, headers, lambda: None)
    assert len(peer["requests"]) == 1
    with pytest.raises(NativeHeld, match="unapproved"):
        AhvHttp(endpoint, read_only=True).call(
            "POST", COLLECTIONS["image"], {}, headers, lambda: None
        )
    assert len(peer["requests"]) == 1


@pytest.mark.parametrize("fault", ["", "platform", "firmware"])
def test_prepared_guest_copy_must_match_destination_platform_and_firmware(
    campaign: dict[str, Any],
    fault: str,
) -> None:
    c = campaign
    c["receipt"].update(
        guest_transformation="prepared_offline",
        guest_target_platform="openstack" if fault == "platform" else "ahv",
        guest_firmware="efi" if fault == "firmware" else "bios",
    )
    if fault:
        with pytest.raises(NativeHeld):
            c["execution"].execute(c["binding"])
        assert not c["peer"].posts
    else:
        assert c["execution"].execute(c["binding"])["observation"]["outcome"] == "observed_present"



def test_ahv_transport_requires_exact_commissioned_namespace_before_network(
    platform_peer: tuple[NativeEndpoint, dict[str, Any]],
) -> None:
    endpoint, peer = platform_peer
    pinned = dict.fromkeys(("vmm", "prism", "clustermgmt", "networking",
                            "microseg", "iam"), "v4.3")
    api = AhvHttp(endpoint, read_only=True, api_versions=pinned)
    with pytest.raises(NativeHeld, match="version_unqualified"):
        api.call("GET", "/api/vmm/v4.2/ahv/config/vms/" + uid(),
                 None, {}, lambda: None)
    with pytest.raises(NativeHeld, match="version_unqualified"):
        api.call("GET", "/api/prism/v4.2/config/domain-managers/" + uid(),
                 None, {}, lambda: None)
    assert peer["requests"] == []
    with pytest.raises(NativeHeld, match="manifest_invalid"):
        AhvHttp(endpoint, api_versions={"vmm": "v4.3"})
