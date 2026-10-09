"Run a bounded number of leased read pages; restart resumes the persisted cursor."

import argparse
import hashlib
import json
import os
import time
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from inventory_worker.infrastructure.native import (
    CollectionFailure,
    capture_native_reads,
    collect,
    exchange,
    secret,
    strict_json,
)


def document(path: str) -> dict[str, Any]:
    if not os.path.isabs(path):
        raise ValueError("An absolute mounted configuration path is required")
    with Path(path).open("rb") as handle:
        raw = handle.read(1048577)
    if len(raw) > 1048576:
        raise ValueError("Configuration is oversized")
    data = strict_json(raw)
    if not isinstance(data, dict):
        raise ValueError("Invalid configuration")
    return data


def run_page(config: dict[str, Any]) -> bool:
    credential = secret(config["credential_file"])
    headers = {"Authorization": "Bearer " + credential}
    received = exchange(config, "/internal/collections/claim", headers, method="POST", body={})
    job = received["job"]
    if job is None:
        return False
    if not isinstance(job, dict) or set(job) - {"collect_configuration"} != {
        "discovery_id",
        "endpoint_id",
        "policy_id",
        "policy_digest",
        "sequence",
        "stream",
        "cursor",
        "lease_token",
        "lease_until",
    }:
        raise ValueError("Invalid lease")
    policies = document(os.environ["INVENTORY_SITE_POLICIES_FILE"])
    matched = [p for p in policies["policies"] if p["policy_id"] == job["policy_id"]]
    body = {k: job[k] for k in ("discovery_id", "lease_token", "sequence")}
    try:
        if len(matched) != 1:
            raise CollectionFailure("permission_denied")
        p = matched[0]
        digest = hashlib.sha256(
            json.dumps(p, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
        ).hexdigest()
        if (
            digest != job["policy_digest"]
            or p["worker_fingerprint"] != hashlib.sha256(credential.encode()).hexdigest()
            or p["expires_at"] <= time.time()
            or not time.time() < job["lease_until"] <= time.time() + 31
        ):
            raise CollectionFailure("permission_denied")
        request_number = 0

        def before_request() -> None:
            nonlocal request_number
            request_number += 1
            while time.time() + 12 < job["lease_until"] and time.time() < p["expires_at"]:
                permit = exchange(
                    config,
                    "/internal/collections/profile-reads",
                    headers,
                    method="POST",
                    body={**body, "request_number": request_number},
                )
                if not isinstance(permit, dict) or set(permit) != {"allowed", "retry_after"}:
                    raise CollectionFailure("invalid_response")
                if permit["allowed"] is True and time.time() + 10 < job["lease_until"]:
                    return
                delay = permit["retry_after"]
                if (
                    permit["allowed"] is not False
                    or type(delay) not in {int, float}
                    or not 0 < delay <= 2
                ):
                    raise CollectionFailure("permission_denied")
                time.sleep(delay)
            raise CollectionFailure("permission_denied")

        native_get_receipts: list[dict[str, Any]] = []

        def receipt(witness: dict[str, Any]) -> None:
            if (len(native_get_receipts) >= 128
                    or not isinstance(witness.get("native_operation"), str)
                    or len(witness["native_operation"]) > 404):
                raise CollectionFailure("invalid_response")
            native_get_receipts.append(witness)

        # The page and its GET witnesses are published in one lease-bound,
        # idempotent Inventory transaction. The independently signed coverage
        # record is assembled from these observed facts later, never invented.
        with capture_native_reads(receipt):
            page = collect(
                p, job["stream"], job["cursor"],
                job.get("collect_configuration", False), before_request,
            )
        body.update(page)
        if native_get_receipts:
            body["native_read_receipts"] = native_get_receipts
    except CollectionFailure as error:
        body.update(
            observations=[],
            next_cursor=None,
            terminal=False,
            coverage=False,
            collected_at=time.time(),
            error=error.reason,
        )
    # A lost response is retried unchanged; never repeat the native request in this lease.
    for attempt in range(2):
        try:
            exchange(config, "/internal/collections/pages", headers, method="POST", body=body)
            return True
        except CollectionFailure:
            if attempt or time.time() >= job["lease_until"]:
                raise
    return False


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="inventory-worker-collect", allow_abbrev=False)
    parser.add_argument("--pages", type=int, default=1)
    args = parser.parse_args(argv)
    if not 1 <= args.pages <= 100:
        parser.error("pages must be between 1 and 100")
    try:
        for _ in range(args.pages):
            config = document(os.environ["INVENTORY_CONTROL_PLANE_FILE"])
            if not run_page(config):
                break
        return 0
    except (KeyError, TypeError, ValueError, OSError, CollectionFailure):
        # Non-sensitive status only. The persisted lease/retry state owns recovery.
        print('{"status":"collection_unavailable"}')
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
