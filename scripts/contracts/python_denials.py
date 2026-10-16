"""Exercise unauthenticated requests against the *real* composed Python ASGI routers.

A missing token is not considered an authentication denial if the runtime
instead returns a routing error, dependency failure, timeout or success.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import tempfile
from pathlib import Path
from unittest.mock import patch

from assurance import inventory

ROOT = Path(__file__).resolve().parents[2]
UUID = "10000000-0000-4000-8000-000000000001"


def actual_path(template: str) -> str:
    def substitute(match: re.Match[str]) -> str:
        name = match.group(1)
        return ("a" * 64 if name in {"digest", "sha256", "fingerprint"}
                else "1" if name in {"revision", "sequence"} else UUID)
    return re.sub(r"\{([A-Za-z_][A-Za-z_0-9]*)\}", substitute, template)


async def exchange(app, method: str, uri: str) -> int:
    sent = []
    first = True

    async def receive():
        nonlocal first
        if first:
            first = False
            return {"type": "http.request", "body": b"{}", "more_body": False}
        return {"type": "http.disconnect"}

    async def send(message):
        sent.append(message)

    scope = {
        "type": "http", "asgi": {"version": "3.0", "spec_version": "2.3"},
        "http_version": "1.1", "method": method, "scheme": "http",
        "path": uri, "raw_path": uri.encode("ascii"), "query_string": b"",
        "root_path": "", "headers": [(b"accept", b"application/json"),
                                      (b"content-type", b"application/json")],
        "client": ("127.0.0.1", 4444), "server": ("127.0.0.1", 8080),
        "state": {},
    }
    await asyncio.wait_for(app(scope, receive, send), timeout=7.0)
    statuses = [message["status"] for message in sent
                if message["type"] == "http.response.start"]
    if len(statuses) != 1:
        raise ValueError("No unique runtime HTTP response: " + method + " " + uri)
    return statuses[0]


def get_app(owner: str):
    if owner == "inventory":
        from inventory.bootstrap.server import create_app
        from inventory.interfaces.discovery import ROUTES
        from inventory.interfaces.planning import PlanningInputApp
        return create_app()
    if owner == "planning":
        from planning.bootstrap.server import create_app
        return create_app()
    if owner == "lifecycle":
        from lifecycle.bootstrap.server import create_app
        return create_app()
    raise ValueError("No composed Python router for: " + owner)


async def probe(owner: str) -> tuple[list[dict], list[str]]:
    """Enrol an independent ephemeral inbound principal for auth-denial probes.

    The service's real credential loader must succeed before a missing token
    can prove 401. A missing test mount is a 503 dependency failure, not an
    authentication observation. Never add a production credential fallback.
    """
    if owner != "planning" or os.environ.get(
        "PLANNING_ASSURANCE_INVALIDATION_CREDENTIAL_FILE"
    ):
        return await _probe_with_router(owner)
    with tempfile.TemporaryDirectory(prefix="planning-invalidation-probe-") as folder:
        credential = Path(folder) / "inbound-credential"
        credential.write_text("synthetic-independent-denial-principal-" + "q" * 64)
        credential.chmod(0o600)
        with patch.dict(os.environ, {
            "PLANNING_ASSURANCE_INVALIDATION_CREDENTIAL_FILE": str(credential),
        }):
            return await _probe_with_router(owner)


async def _probe_with_router(owner: str) -> tuple[list[dict], list[str]]:
    operations = inventory()["operations"]
    try:
        app = get_app(owner)
    except Exception as error:
        # A missing development secret or service bootstrap is NOT proof of
        # a denial. Preserve the coverage report, mark all owned probes absent,
        # and let the aggregate release gate fail closed.
        return [], [owner + " router-unavailable:" + type(error).__name__]
    measured = []
    unresolved = []
    eligible = 0
    for op in operations:
        if op["owner"] != owner or not op["security_required"]:
            continue
        # Native control has a separate service composition, and native worker
        # effects run in separate process boundaries; never claim coverage via
        # the ordinary Lifecycle simulation router.
        if (owner == "lifecycle"
                and op["release"] in {
                    "contracts/openapi/lifecycle-migration-boundary-v2.json",
                    "contracts/openapi/lifecycle-native-jobs-v1.1.json",
                    "contracts/openapi/worker-migration-effect-v2.1.json",
                }):
            continue
        eligible += 1
        try:
            code = await exchange(app, op["method"], actual_path(op["path"]))
        except Exception as error:
            unresolved.append(op["key"] + " runtime-error:" + type(error).__name__)
            continue
        if code not in (401, 403):
            unresolved.append(op["key"] + " unsupported-denial:" + str(code))
            continue
        measured.append({
            "key": op["key"], "claim": "authentication",
            "source": "live-denial", "result": "PASS",
            "release_sha256": op["release_sha256"],
            "test": "python_denials.py:unauthenticated_" + str(code),
            "denial_kind": "missing-credential", "status_code": code,
        })
    if eligible == 0:
        unresolved.append(owner + " no-secured-runtime-operations-exercised")
    for observation in measured:
        observation["run_id"] = os.environ.get("GITHUB_RUN_ID")
        observation["run_attempt"] = os.environ.get("GITHUB_RUN_ATTEMPT")
        observation["revision"] = os.environ.get("GITHUB_SHA")
    return measured, unresolved


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--owner", choices=("inventory", "planning", "lifecycle"),
                        required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    measured, unresolved = asyncio.run(probe(args.owner))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(measured, indent=2) + "\n")
    print(json.dumps({"owner": args.owner, "verified_denials": len(measured),
                      "unresolved": unresolved[:35], "unresolved_total": len(unresolved)}))
    # Never mark the service probe green when the router could not start,
    # a secure route could not execute, or an unauthenticated request escaped
    # with a non-denial status. The evidence file is retained for diagnosis.
    return int(bool(unresolved))


if __name__ == "__main__":
    raise SystemExit(main())
