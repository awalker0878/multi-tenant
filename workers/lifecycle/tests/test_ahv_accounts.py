"""AHV commissioning combines native state with separately protected key custody."""

import hashlib
from collections.abc import Callable
from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest

from lifecycle_worker.application.native import NativeHeld, digest
from lifecycle_worker.infrastructure.ahv_accounts import probe
from lifecycle_worker.infrastructure.native_http import NativeEndpoint


@pytest.mark.parametrize("fault", ["", "secret", "user", "key", "expiry", "policy"])
def test_key_creation_binding_live_iam_and_policy_changes(tmp_path: Path, fault: str) -> None:
    user, key, policy_id = [str(uuid4()) for _ in range(3)]
    token = tmp_path / "token"
    token.write_text("synthetic-key-creation-secret")
    token.chmod(0o600)
    endpoint = NativeEndpoint("https://pc.invalid", "192.0.2.1", tmp_path / "ca", token)
    policy = {"extId": policy_id, "displayName": "scoped migration"}
    account = {
        "user_id": user,
        "key_id": key,
        "credential_sha256": hashlib.sha256(token.read_bytes()).hexdigest(),
        "authorization_policies": {policy_id: digest(policy)},
        "endpoint": {},
    }
    calls = []

    class Peer:
        def call(
            self,
            method: str,
            path: str,
            body: Any,
            headers: dict[str, str],
            boundary: Callable[[], None],
        ) -> dict[str, Any]:
            boundary()
            calls.append(path)
            assert method == "GET"
            if "/authorization-policies/" in path:
                row = policy | ({"displayName": "changed"} if fault == "policy" else {})
            elif "/keys/" in path:
                row = {
                    "extId": key,
                    "keyType": "API_KEY",
                    "status": "REVOKED" if fault == "key" else "ACTIVE",
                    "expiryTime": "1970-01-01T00:00:00Z"
                    if fault == "expiry"
                    else "2099-01-01T00:00:00Z",
                }
            else:
                row = {
                    "extId": str(uuid4()) if fault == "user" else user,
                    "userType": "SERVICE_ACCOUNT",
                    "status": "ACTIVE",
                }
            return {"document": {"data": row}, "etag": ""}

    if fault == "secret":
        token.write_text("different-key")
    if fault:
        with pytest.raises(NativeHeld):
            probe(Peer(), account, endpoint, lambda: 100, lambda: None)
    else:
        result = probe(Peer(), account, endpoint, lambda: 100, lambda: None)
        assert result["identity_source"] == "protected_key_creation_receipt_and_live_iam"
        assert result["native_effects_qualified"] is False
        assert "synthetic-key" not in str(result)
    if fault == "secret":
        assert not calls
