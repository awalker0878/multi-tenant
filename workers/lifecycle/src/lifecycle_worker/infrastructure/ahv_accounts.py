"""AHV key-creation custody plus current read-only IAM observations.

IAM never returns a key's secret again. A protected creation receipt binds the
secret hash to its native user/key IDs; GETs alone do not prove caller identity.
Authorization policy names alone never establish permission or native support.
"""

import hashlib
from collections.abc import Callable
from datetime import datetime
from typing import Any

from lifecycle_worker.application.api_plan import shape
from lifecycle_worker.application.native import NativeHeld, digest, identity, sha256
from lifecycle_worker.infrastructure.ahv_http import AhvTransport, read
from lifecycle_worker.infrastructure.native_http import NativeEndpoint, credential


def validate_account(account: dict[str, Any], endpoint: NativeEndpoint) -> None:
    shape(account, {"user_id", "key_id", "credential_sha256", "authorization_policies", "endpoint"})
    identity(account["user_id"])
    identity(account["key_id"])
    policies = account["authorization_policies"]
    if (
        not sha256(account["credential_sha256"])
        or hashlib.sha256(credential(endpoint).encode()).hexdigest() != account["credential_sha256"]
        or not isinstance(policies, dict)
        or not 1 <= len(policies) <= 16
    ):
        raise NativeHeld("ahv_key_creation_receipt_changed")
    for key, value in policies.items():
        identity(key)
        if not sha256(value):
            raise NativeHeld("invalid_ahv_authorization_receipt")


def probe(
    api: AhvTransport,
    account: dict[str, Any],
    endpoint: NativeEndpoint,
    clock: Callable[[], int],
    current: Callable[[], None],
) -> dict[str, Any]:
    def check() -> None:
        current()
        validate_account(account, endpoint)

    check()
    root = "/api/iam/v4.3/authn/users/" + account["user_id"]
    user = read(api, root, check)
    key = read(api, root + "/keys/" + account["key_id"], check)
    try:
        expiry = datetime.fromisoformat(key["expiryTime"].replace("Z", "+00:00"))
        valid_expiry = expiry.tzinfo is not None and expiry.timestamp() > clock()
    except (KeyError, TypeError, ValueError):
        valid_expiry = False
    if (
        user.get("extId") != account["user_id"]
        or user.get("userType") != "SERVICE_ACCOUNT"
        or user.get("status") != "ACTIVE"
        or key.get("extId") != account["key_id"]
        or key.get("status") != "ACTIVE"
        or key.get("keyType") != "API_KEY"
        or not valid_expiry
    ):
        raise NativeHeld("ahv_account_revoked_or_expired")
    for policy_id, expected in account["authorization_policies"].items():
        policy = read(api, "/api/iam/v4.3/authz/authorization-policies/" + policy_id, check)
        if policy.get("extId") != policy_id or digest(policy) != expected:
            raise NativeHeld("ahv_authorization_policy_changed")
    return {
        "identity_sha256": digest([account["user_id"], account["key_id"]]),
        "identity_source": "protected_key_creation_receipt_and_live_iam",
        "evidence_sha256": digest([user, key, account["authorization_policies"]]),
        "native_effects_qualified": False,
    }
