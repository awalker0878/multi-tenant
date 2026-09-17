#!/usr/bin/env python3
"""Offline, read-only Terraform JSON-plan review triggers. Never authorizes execution.

Only action metadata and presence of unknown fields are examined; before/after
resource values are never included in output. Resource addresses themselves may
be sensitive. Run only on a protected, authorized copy of the JSON plan.
"""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path
from typing import Any

ALLOWED_ACTIONS = {"no-op", "create", "read", "update", "delete", "forget"}
MAX_BYTES = 100 * 1024 * 1024

class PlanError(ValueError):
    pass

def unknown_present(value: Any) -> bool:
    if isinstance(value, dict):
        return any(unknown_present(v) for v in value.values())
    if isinstance(value, list):
        return any(unknown_present(v) for v in value)
    return value is True

def review(plan: Any) -> dict[str, Any]:
    if not isinstance(plan, dict):
        raise PlanError("Root must be a JSON object.")
    if not isinstance(plan.get("format_version"), str):
        raise PlanError("Missing JSON plan format_version; a state file is not a plan.")
    if plan["format_version"].split(".")[0] != "1":
        raise PlanError("Unsupported JSON plan major format; review the tool before use.")
    if "planned_values" not in plan or not isinstance(plan["planned_values"], dict):
        raise PlanError("Missing planned_values object; input is not a supported saved-plan export.")
    if "resource_changes" not in plan:
        # Do not report 'no changes' from an omitted section.
        raise PlanError("resource_changes is absent; this tool cannot distinguish omission from no changes. Supply an explicit array after checking the source export.")
    changes = plan["resource_changes"]
    if not isinstance(changes, list):
        raise PlanError("resource_changes must be an array.")
    for field in ("resource_drift", "deferred_changes"):
        if field in plan and not isinstance(plan[field], list):
            raise PlanError(f"{field} must be an array when present.")
    out: dict[str, Any] = {
        "tool": "offline-plan-review-v1.0",
        "authorization": "NOT EVALUATED — this report never authorizes plan or apply",
        "limits": "Metadata-only screen. No policy, topology, provider support, credentials, evidence, or actual state evaluated. No infrastructure contacted.",
        "resource_count": len(changes),
        "change_actions": [],
        "review_triggers": [],
    }
    seen: set[str] = set()
    for i, item in enumerate(changes):
        if not isinstance(item, dict) or not isinstance(item.get("address"), str) or not item["address"].strip():
            raise PlanError(f"resource_changes[{i}] lacks a nonempty resource address.")
        address = item["address"]
        if address in seen:
            raise PlanError(f"Duplicate resource address at index {i}.")
        seen.add(address)
        change = item.get("change")
        if not isinstance(change, dict):
            raise PlanError(f"resource_changes[{i}] lacks a change object.")
        actions = change.get("actions")
        if not isinstance(actions, list) or not actions or any(not isinstance(a, str) or a not in ALLOWED_ACTIONS for a in actions):
            raise PlanError(f"resource_changes[{i}] has unsupported or missing actions.")
        supported_sequences = [["no-op"],["create"],["read"],["update"],["delete"],["forget"],["create","delete"],["delete","create"]]
        if actions not in supported_sequences:
            raise PlanError(f"resource_changes[{i}] has an unrecognized action sequence.")
        out["change_actions"].append({"address": address, "actions": actions})
        if "delete" in actions:
            label = "replacement" if "create" in actions else "deletion"
            out["review_triggers"].append({"resource": address, "trigger": label, "review": "Confirm ownership, data/copy/hold impact, supported recovery, approved window and dependent paths."})
        if "forget" in actions:
            out["review_triggers"].append({"resource": address, "trigger": "management removed", "review": "Confirm explicit ownership transfer; forgetting state is not resource retirement."})
        if "after_unknown" in change and unknown_present(change["after_unknown"]):
            out["review_triggers"].append({"resource": address, "trigger": "values unknown until apply", "review": "Review whether deferred values affect security, placement, routing, identity or data scope."})
        if item.get("previous_address"):
            out["review_triggers"].append({"resource": address, "trigger": "resource address moved", "review": "Verify intended identity/ownership transfer and no destructive side effect."})
    if plan.get("resource_drift"):
        out["review_triggers"].append({"trigger": "drift present", "count": len(plan["resource_drift"]), "review": "Review actual native state and any incident containment before reconciling."})
    if plan.get("deferred_changes"):
        out["review_triggers"].append({"trigger": "deferred changes present", "count": len(plan["deferred_changes"]), "review": "This export does not fully resolve the intended change set."})
    if plan.get("complete") is False:
        out["review_triggers"].append({"trigger": "plan explicitly incomplete", "review": "Resolve and review remaining work; do not treat this report as complete scope."})
    if plan.get("errored") is True:
        out["review_triggers"].append({"trigger": "plan errored", "review": "Stop; resolve the plan error before any execution decision."})
    if not out["review_triggers"]:
        out["summary"] = "No selected metadata trigger found; semantic and authority review is still required."
    else:
        out["summary"] = "Selected metadata requires explicit review; no approval or safety verdict is issued."
    return out

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan_json", type=Path)
    args = parser.parse_args(argv)
    try:
        if not args.plan_json.is_file():
            raise PlanError("Input file does not exist.")
        if args.plan_json.stat().st_size > MAX_BYTES:
            raise PlanError("Input exceeds the 100 MiB local review limit.")
        report = review(json.loads(args.plan_json.read_text(encoding="utf-8-sig")))
    except (OSError, UnicodeError, json.JSONDecodeError, PlanError, RecursionError) as exc:
        # Do not echo JSON contents, native values, or full file path in errors.
        message = str(exc) if isinstance(exc, PlanError) else type(exc).__name__
        print(json.dumps({"error": message, "authorization": "NOT EVALUATED"}), file=sys.stderr)
        return 2
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 1 if report["review_triggers"] else 0

if __name__ == "__main__":
    raise SystemExit(main())
