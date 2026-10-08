"""Exact native identities and privilege responses; peers are synthetic, no live account proof."""

import json
from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest

from lifecycle_worker.application.native import NativeHeld
from lifecycle_worker.infrastructure.migration_accounts import MigrationAccountProbe


def manifest(tmp_path: Path) -> tuple[Path, dict[str, Any]]:
    source: dict[str, Any] = {}
    target: dict[str, Any] = {}
    for side, accounts in (("source", source), ("target", target)):
        for role in ("collector", "writer", "observer"):
            token = tmp_path / (side + role + ".token")
            token.write_text(side + role + "-" + "a" * 32)
            connection = {
                "base_url": "https://native.invalid",
                "address": "192.0.2.1",
                "ca_file": str(tmp_path / "ca"),
                "token_file": str(token),
            }
            accounts[role] = (
                {
                    "user_name": role,
                    "endpoint": connection,
                    "privileges": [
                        {
                            "entity": {"type": "VirtualMachine", "value": "vm-5"},
                            "required": ["System.View"],
                            "forbidden": ["VirtualMachine.Interact.PowerOn"],
                        }
                    ],
                }
                if side == "source"
                else {
                    "user_id": str(uuid4()),
                    "endpoints": {
                        service: connection
                        for service in ("identity", "compute", "network", "volume")
                    },
                    "roles": ["reader" if role != "writer" else "member"],
                }
            )
    config = {
        "schema_version": 1,
        "scope": {k: str(uuid4()) for k in ("tenant_id", "site_id", "environment", "executor_id")},
        "expires_at": 200,
        "source": {
            "api_version": "8.0.3.0",
            "instance_uuid": str(uuid4()),
            "session_manager": "SessionManager",
            "authorization_manager": "AuthorizationManager",
            "accounts": source,
        },
        "target": {"project_id": str(uuid4()), "accounts": target},
    }
    path = tmp_path / "accounts.json"
    path.write_text(json.dumps(config))
    return path, config


@pytest.mark.parametrize(
    "fault",
    [
        None,
        "foreign_source",
        "source_user",
        "missing_privilege",
        "forbidden_privilege",
        "duplicate_privilege",
        "foreign_project",
        "extra_role",
        "expired_token",
        "rotated_manifest",
        "shared_token",
    ],
)
def test_commissioning_checks_current_native_identity_scope_and_privileges(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fault: str | None
) -> None:
    path, config = manifest(tmp_path)
    requests: list[str] = []

    def request(
        api: Any, method: str, route: str, boundary: Any, body: Any = None, expected: int = 200
    ) -> Any:
        boundary()
        requests.append(route)
        role = next(
            k
            for k, v in config["source"]["accounts"].items()
            if v["endpoint"]["token_file"] == str(api.endpoint.token_file)
        )
        if route.endswith("/currentSession"):
            return {
                "userName": "other" if fault == "source_user" else role,
                "key": "secret-session-never-exported",
            }
        if route.endswith("/content"):
            return {
                "about": {
                    "instanceUuid": str(uuid4())
                    if fault == "foreign_source"
                    else config["source"]["instance_uuid"]
                }
            }
        assert method == "POST" and route.endswith("/HasUserPrivilegeOnEntities")
        permissions = [{"privId": k, "isGranted": k == "System.View"} for k in body["privId"]]
        if fault == "missing_privilege":
            permissions = permissions[:1]
        if fault == "duplicate_privilege":
            permissions = [permissions[0], permissions[0]]
        if fault == "forbidden_privilege":
            permissions[-1]["isGranted"] = True
        if fault == "rotated_manifest":
            path.write_text("{}")
        return [{"entity": body["entities"][0], "privAvailability": permissions}]

    def get(reads: Any, service: str, route: str, *, subject: bool = False) -> Any:
        requests.append(service + route)
        role = next(
            k
            for k, v in config["target"]["accounts"].items()
            if v["endpoints"]["identity"]["token_file"]
            == str(reads.endpoints["identity"].token_file)
        )
        account = config["target"]["accounts"][role]
        if service == "identity":
            return {
                "token": {
                    "user": {"id": account["user_id"]},
                    "project": {
                        "id": str(uuid4())
                        if fault == "foreign_project"
                        else config["target"]["project_id"]
                    },
                    "expires_at": "1970-01-01T00:01:39Z"
                    if fault == "expired_token"
                    else "2100-01-01T00:00:00Z",
                    "roles": [
                        {"name": k}
                        for k in account["roles"] + (["admin"] if fault == "extra_role" else [])
                    ],
                }
            }
        return {"observed": True}

    monkeypatch.setattr(
        "lifecycle_worker.infrastructure.migration_accounts.NativeJson.request", request
    )
    monkeypatch.setattr("lifecycle_worker.infrastructure.migration_accounts.NativeReads.get", get)
    if fault == "shared_token":
        account = config["target"]["accounts"]["observer"]
        Path(account["endpoints"]["identity"]["token_file"]).write_text(
            Path(
                config["target"]["accounts"]["writer"]["endpoints"]["identity"]["token_file"]
            ).read_text()
        )
    if fault:
        with pytest.raises(NativeHeld):
            MigrationAccountProbe(path, lambda: 100).run()
    else:
        report = MigrationAccountProbe(path, lambda: 100).run()
        assert len(report["accounts"]) == 6 and report["accounts_checked"]
        assert report["native_effects_qualified"] is False
        assert "secret-session" not in json.dumps(report)
        assert len(requests) == 21


def matrix_manifest(tmp_path: Path, source: str, target: str) -> tuple[Path, dict[str, Any]]:
    import hashlib

    from lifecycle_worker.application.native import digest

    path, config = manifest(tmp_path)
    originals = config["source"], config["target"]
    config["schema_version"] = 3
    for side, platform in (("source", source), ("target", target)):
        row: dict[str, Any] = {"platform": platform, "accounts": {}}
        if platform == "vmware":
            row.update({k: v for k, v in originals[0].items() if k != "accounts"})
            row["instance_uuid"] = str(uuid4())
        else:
            row["project_id"] = str(uuid4())
            if platform == "ahv":
                row.update(prism_central_id=str(uuid4()), cluster_id=str(uuid4()))
        for role in ("collector", "writer", "observer"):
            token = tmp_path / (side + role + ".token")
            token.write_text(side + role + "-" + "a" * 32)
            connection = {
                "base_url": "https://" + side + ".invalid",
                "address": "192.0.2.1" if side == "source" else "192.0.2.2",
                "ca_file": str(tmp_path / "ca"),
                "token_file": str(token),
            }
            account = (
                {**originals[0]["accounts"][role], "endpoint": connection}
                if platform == "vmware"
                else {
                    "user_id": str(uuid4()),
                    "endpoints": {
                        service: connection
                        for service in ("identity", "compute", "volume", "network")
                    },
                    "image": connection,
                    "roles": ["reader" if role != "writer" else "member"],
                }
                if platform == "openstack"
                else {
                    "user_id": str(uuid4()),
                    "key_id": str(uuid4()),
                    "credential_sha256": hashlib.sha256(token.read_bytes()).hexdigest(),
                    "authorization_policies": {},
                    "endpoint": connection,
                }
            )
            if platform == "ahv":
                policy = {"extId": str(uuid4()), "status": "ACTIVE"}
                account["authorization_policies"] = {policy["extId"]: digest(policy)}
            row["accounts"][role] = account
        config[side] = row
    path.write_text(json.dumps(config))
    return path, config


def install_matrix_peers(config: dict[str, Any], monkeypatch: pytest.MonkeyPatch) -> list[str]:
    calls: list[str] = []

    def find(token_path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
        return next(
            (row, account)
            for row in (config["source"], config["target"])
            for account in row["accounts"].values()
            if str(token_path)
            == (
                account["endpoints"]["identity"]["token_file"]
                if row["platform"] == "openstack"
                else account["endpoint"]["token_file"]
            )
        )

    def request(
        api: Any, method: str, route: str, boundary: Any, body: Any = None, expected: int = 200
    ) -> Any:
        boundary()
        calls.append(route)
        row, account = find(api.endpoint.token_file)
        if route.endswith("/schemas/image"):
            return {"name": "image"}
        if route.endswith("/currentSession"):
            return {"userName": account["user_name"]}
        if route.endswith("/content"):
            return {"about": {"instanceUuid": row["instance_uuid"]}}
        assert method == "POST" and route.endswith("/HasUserPrivilegeOnEntities")
        return [
            {
                "entity": body["entities"][0],
                "privAvailability": [
                    {"privId": key, "isGranted": key == "System.View"} for key in body["privId"]
                ],
            }
        ]

    def get(api: Any, service: str, route: str, *, subject: bool = False) -> Any:
        api.identity_check()
        calls.append(service + route)
        row, account = find(api.endpoints["identity"].token_file)
        if service == "identity":
            return {
                "token": {
                    "user": {"id": account["user_id"]},
                    "project": {"id": row["project_id"]},
                    "expires_at": "2100-01-01T00:00:00Z",
                    "roles": [{"name": name} for name in account["roles"]],
                }
            }
        return {"observed": True}

    def ahv_call(api: Any, method: str, route: str, body: Any, headers: Any, boundary: Any) -> Any:
        boundary()
        calls.append(route)
        row, account = find(api.endpoint.token_file)
        key = route.rsplit("/", 1)[-1]
        data = {"extId": key, "status": "ACTIVE"}
        if "/keys/" in route:
            data.update(keyType="API_KEY", expiryTime="2100-01-01T00:00:00Z")
        elif "/users/" in route:
            data["userType"] = "SERVICE_ACCOUNT"
        return {"document": {"data": data}, "etag": "etag"}

    monkeypatch.setattr(
        "lifecycle_worker.infrastructure.migration_accounts.NativeJson.request", request
    )
    monkeypatch.setattr("lifecycle_worker.infrastructure.migration_accounts.NativeReads.get", get)
    monkeypatch.setattr("lifecycle_worker.infrastructure.ahv_http.AhvHttp.call", ahv_call)
    return calls


@pytest.mark.parametrize("source", ["vmware", "openstack", "ahv"])
@pytest.mark.parametrize("target", ["vmware", "openstack", "ahv"])
def test_all_nine_directional_account_sets_use_native_role_scoped_probes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, source: str, target: str
) -> None:
    path, config = matrix_manifest(tmp_path, source, target)
    calls = install_matrix_peers(config, monkeypatch)
    report = MigrationAccountProbe(path, lambda: 100).run()
    assert len(report["accounts"]) == 6
    assert {(r["side"], r["platform"], r["role"]) for r in report["accounts"]} == {
        (side, platform, role)
        for side, platform in (("source", source), ("target", target))
        for role in ("collector", "writer", "observer")
    }
    counts = {"vmware": 9, "openstack": 15, "ahv": 15}
    assert len(calls) == counts[source] + counts[target]
    assert report["accounts_checked"] and report["native_effects_qualified"] is False


@pytest.mark.parametrize("fault", ["origin", "token", "image", "rotation"])
def test_directional_account_probes_fail_closed_before_accepting_mixed_identity(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fault: str
) -> None:
    path, config = matrix_manifest(tmp_path, "openstack", "vmware")
    install_matrix_peers(config, monkeypatch)
    account = config["source"]["accounts"]["observer"]
    if fault == "origin":
        account["image"] = account["image"] | {"address": "192.0.2.3"}
    elif fault == "token":
        token = tmp_path / "different.token"
        token.write_text("different-" + "x" * 32)
        account["image"] = account["image"] | {"token_file": str(token)}
    elif fault == "image":
        del account["image"]
    else:
        original = MigrationAccountProbe.openstack

        def rotate(self: Any, row: Any, role: str, current: Any) -> Any:
            Path(row["accounts"][role]["image"]["token_file"]).write_text("rotated-" + "x" * 32)
            return original(self, row, role, current)

        monkeypatch.setattr(MigrationAccountProbe, "openstack", rotate)
    path.write_text(json.dumps(config))
    with pytest.raises(NativeHeld):
        MigrationAccountProbe(path, lambda: 100).run()
