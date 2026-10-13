#!/usr/bin/env python3
"""One stable PR status: no skipped or failed required affected validation."""
from __future__ import annotations
import json
import os
import sys


def verify(needs: dict) -> list[str]:
    problems = []
    scope = needs.get("scope", {})
    if scope.get("result") != "success":
        return ["scope must succeed"]
    flags = scope.get("outputs", {})
    for family in ("python", "php"):
        try:
            selected = json.loads(flags[family])
            if not isinstance(selected, list) or any(not isinstance(x, str) for x in selected):
                raise ValueError("invalid selection")
            if len(selected) != len(set(selected)):
                raise ValueError("duplicate selected component")
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            problems.append(f"{family} selection invalid: {exc}")
            continue
        expected = "success" if selected else "skipped"
        observed = needs.get(family, {}).get("result")
        if observed != expected:
            problems.append(f"{family}: expected {expected}, got {observed}")
    for job, flag in (("architecture", "docs"), ("contracts", "contracts"),
                      ("contract-assurance", "contracts"),
                      ("security", "security"), ("native", "native"),
                      ("authority", "authority"), ("laravel-routes", "routes")):
        if flags.get(flag) not in ("true", "false"):
            problems.append(f"invalid {flag} affected flag")
            continue
        expected = "success" if flags[flag] == "true" else "skipped"
        if needs.get(job, {}).get("result") != expected:
            problems.append(f"{job}: expected {expected}, got {needs.get(job, {}).get('result')}")
    return problems


if __name__ == "__main__":
    errors = verify(json.loads(os.environ.get("CI_NEEDS_JSON", "{}")))
    for error in errors:
        print("ERROR:", error, file=sys.stderr)
    if errors:
        sys.exit(1)
    print("All affected checks passed; unaffected checks were intentionally skipped.")
