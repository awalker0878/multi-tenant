"""Exercise unauthenticated requests against the *real* composed Python ASGI routers.

A missing token is not considered an authorization denial if the runtime
instead returns a routing error, dependency failure, timeout or success.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
from pathlib import Path

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
    app = get_app(owner)
    operations = inventory()["operations"]
    measured = []
    unresolved = []
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
        try:
            code = await exchange(app, op["method"], actual_path(op["path"]))
        except Exception as error:
            unresolved.append(op["key"] + " runtime-error:" + type(error).__name__)
            continue
        if code not in (401, 403):
            unresolved.append(op["key"] + " unsupported-denial:" + str(code))
            continue
        measured.append({
            "key": op["key"], "claim": "authorization",
            "source": "live-denial", "result": "PASS",
            "release_sha256": op["release_sha256"],
            "test": "python_denials.py:unauthenticated_" + str(code),
        })
    for observation in measured:
        observation["run_id"] = os.environ.get("GITHUB_RUN_ID")
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
    # Incomplete probes remain unqualified in the aggregate report; a success
    # here NEVER claims that all interfaces are ready for release.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
