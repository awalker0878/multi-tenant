#!/usr/bin/env python3
"""Read-only qualification shadow reconciliation. Never publishes native support.

An input manifest is an independently captured observation, not authentication
or native assurance; divergences must be reviewed, never auto-promoted.
"""

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

HASH = re.compile(r"[a-f0-9]{64}\Z")
REVISION = re.compile(r"[a-f0-9]{40}\Z")
STATES = {"unknown", "qualified", "suspended", "revoked"}
LEVELS = {None, "E2", "E3", "E4"}
KEYS = {
    "scope_sha256",
    "authority_epoch",
    "state",
    "decision_sha256",
    "evidence_level",
    "definition_sha256",
    "platform",
    "method",
    "expires_at",
}


def fail(reason: str) -> None:
    raise ValueError("shadow_manifest_invalid: " + reason)


def document(path: Path) -> tuple[dict[str, Any], str]:
    if not path.is_file() or path.is_symlink():
        fail("file unavailable")
    raw = path.read_bytes()
    if not raw or len(raw) > 1048576:
        fail("manifest bound")
    try:
        value = json.loads(raw, parse_constant=lambda _: fail("numeric constant"))
    except (UnicodeError, json.JSONDecodeError) as e:
        raise ValueError("shadow_manifest_invalid: parse") from e
    if type(value) is not dict or set(value) != {"schema_version", "source_revision", "records"}:
        fail("document keys")
    if value["schema_version"] != 1 or not isinstance(value["source_revision"], str):
        fail("manifest version")
    if REVISION.fullmatch(value["source_revision"]) is None:
        fail("source revision")
    rows = value["records"]
    if type(rows) is not list or len(rows) > 500:
        fail("record bound")
    seen: set[str] = set()
    for item in rows:
        if type(item) is not dict or set(item) != KEYS:
            fail("record keys")
        scope = item["scope_sha256"]
        if not isinstance(scope, str) or not HASH.fullmatch(scope) or scope in seen:
            fail("duplicate/invalid scope")
        seen.add(scope)
        epoch = item["authority_epoch"]
        if type(epoch) is not int or not 0 <= epoch <= 2**53 - 1:
            fail("epoch")
        if item["state"] not in STATES or item["evidence_level"] not in LEVELS:
            fail("state/evidence level")
        for key in ("decision_sha256", "definition_sha256"):
            sha = item[key]
            if sha is not None and (not isinstance(sha, str) or not HASH.fullmatch(sha)):
                fail(key)
        if (item["state"] == "qualified" and
                (epoch < 1 or item["decision_sha256"] is None)):
            fail("positive decision without authority")
        for key in ("platform", "method"):
            field = item[key]
            if not isinstance(field, str) or not re.fullmatch(r"[A-Za-z0-9_.:-]{1,80}", field):
                fail("unbounded platform/method")
        expiry = item["expires_at"]
        if type(expiry) is not int or not 0 <= expiry <= 2**53 - 1:
            fail("expiry")
    return value, hashlib.sha256(raw).hexdigest()


def reconcile(before: dict[str, Any], after: dict[str, Any]) -> list[dict[str, Any]]:
    old = {row["scope_sha256"]: row for row in before["records"]}
    new = {row["scope_sha256"]: row for row in after["records"]}
    differences = []
    for scope in sorted(old.keys() | new.keys()):
        a, b = old.get(scope), new.get(scope)
        if a == b:
            continue
        reasons = []
        if a is None:
            reasons.append("new_scope_unreviewed")
        elif b is None:
            reasons.append("removed_scope_unreviewed")
        else:
            if b["authority_epoch"] < a["authority_epoch"]:
                reasons.append("authority_epoch_regression")
            if a["state"] != b["state"]:
                reasons.append("state_changed")
            if (a["state"] != "qualified" and b["state"] == "qualified"):
                reasons.append("positive_support_change_requires_review")
            if a["evidence_level"] != b["evidence_level"]:
                reasons.append("evidence_level_changed_without_external_review")
            if a["decision_sha256"] != b["decision_sha256"]:
                reasons.append("decision_changed")
            if a["definition_sha256"] != b["definition_sha256"]:
                reasons.append("definition_changed")
            if a["platform"] != b["platform"] or a["method"] != b["method"]:
                reasons.append("platform_or_method_changed")
            if a["expires_at"] != b["expires_at"]:
                reasons.append("expiry_changed")
        differences.append({"scope_sha256": scope, "reasons": reasons})
    return differences


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("output must be a new artifact")
    try:
        before, old_hash = document(args.baseline)
        after, new_hash = document(args.candidate)
        diffs = reconcile(before, after)
    except (OSError, ValueError) as e:
        parser.error(str(e))
    # Result never includes untrusted raw records or native promotion requests.
    report = {
        "schema_version": 1,
        "authority": "read_only_shadow_no_promotion",
        "baseline_source_revision": before["source_revision"],
        "candidate_source_revision": after["source_revision"],
        "baseline_manifest_sha256": old_hash,
        "candidate_manifest_sha256": new_hash,
        "status": "REVIEW_REQUIRED" if diffs else "NO_DIFFERENCES",
        "differences": diffs,
        "independent_reviewer_decision": None,
    }
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    return 1 if diffs else 0


if __name__ == "__main__":
    raise SystemExit(main())
