#!/usr/bin/env python3
"""Fail-closed affected CI lane selection using the existing dependency-aware source diff."""
from __future__ import annotations

import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "p01"))
from select_components import changed_paths  # noqa: E402


def classify(paths: list[str] | None) -> dict[str, bool]:
    if paths is None:
        return {name: True for name in ("docs", "contracts", "security", "native", "authority", "routes")}
    def touches(*prefixes: str) -> bool:
        return any(path.startswith(prefixes) for path in paths)
    shared = touches(".github/", "architecture/", "release/", "scripts/ci/", "scripts/p01/", "requirements-docs.txt")
    product = touches("services/", "workers/", "apps/", "packages/")
    contract = touches("contracts/", "tests/contracts/", "scripts/contracts/", "scripts/generate_capabilities.py")
    docs = shared or product or contract or touches("docs/", "tests/documentation/", "scripts/validate_", "scripts/render_delivery_views.py")
    security = shared or product or contract or touches("deploy/", "spikes/compatibility/", "tests/")
    native = shared or contract or touches(
        "services/planning/", "services/inventory/", "services/lifecycle/",
        "workers/lifecycle/", "workers/inventory/", "scripts/p07/", "scripts/p08/",
        "scripts/p09/", "scripts/p10/", "scripts/p04/", "scripts/p05/", "scripts/p06/")
    authority = shared or touches("services/assurance/", "contracts/fixtures/qualification-", "scripts/contracts/")
    routes = shared or contract or touches("services/governance/", "services/catalogue/", "services/assurance/")
    return dict(docs=docs, contracts=shared or product or contract or touches("deploy/"),
                security=security, native=native, authority=authority, routes=routes)


def main() -> None:
    event_path = os.environ.get("GITHUB_EVENT_PATH")
    event = json.loads(Path(event_path).read_text()) if event_path else {}
    paths, reason = changed_paths(event, os.environ.get("GITHUB_EVENT_NAME", "workflow_dispatch"), ROOT)
    result = classify(paths)
    print(json.dumps({"reason": reason, "paths": paths, "lanes": result}, indent=2))
    if os.environ.get("GITHUB_OUTPUT"):
        with Path(os.environ["GITHUB_OUTPUT"]).open("a") as output:
            for key, value in result.items():
                output.write(f"{key}={str(value).lower()}\n")


if __name__ == "__main__":
    main()
