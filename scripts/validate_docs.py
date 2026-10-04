#!/usr/bin/env python3
"""Validate documentation structure and delivery references, not product behavior."""

from pathlib import Path
import re
import sys
from urllib.parse import unquote, urlsplit

import yaml

from render_delivery_views import ROOT, REGISTER, render_views

STATUS = {
    "work": {"NOT_STARTED", "IN_PROGRESS", "COMPLETE"},
    "verification": {"NOT_RUN", "IN_PROGRESS", "PASSED", "FAILED", "NOT_APPLICABLE_REVIEWED"},
    "native_qualification": {"NOT_STARTED", "IN_PROGRESS", "QUALIFIED", "FAILED", "EXPIRED", "NOT_APPLICABLE_REVIEWED"},
    "operational_acceptance": {"NOT_STARTED", "IN_REVIEW", "ACCEPTED", "REJECTED", "NOT_APPLICABLE_REVIEWED"},
}
GATE_VALUES = {"NOT_REVIEWED", "IN_REVIEW", "PASSED", "FAILED"}


def validate():
    errors = []
    def require(condition, message):
        if not condition:
            errors.append(message)
    register = yaml.safe_load(REGISTER.read_text())
    require(register.get("schema_version") == 1, "Unsupported register schema_version")
    collections = {}
    for kind in ("phases", "work_packages", "requirements", "gates", "evidence", "blockers"):
        records = register.get(kind, [])
        ids = [r.get("id") for r in records]
        require(all(ids) and len(ids) == len(set(ids)) if ids else True, f"Missing/duplicate ID in {kind}")
        collections[kind] = {r["id"]: r for r in records}
    phases, packages, requirements, gates, evidence, blockers = (collections[k] for k in collections)

    req_text = (ROOT / "docs/implementation/requirements-and-qualification.md").read_text()
    plan_text = (ROOT / "docs/implementation/phased-plan.md").read_text()
    adr_text = (ROOT / "docs/decisions/decision-register.md").read_text()
    gate_text = (ROOT / "docs/implementation/gates.md").read_text()
    normative_requirements = set(re.findall(r"^\| (R\d+) \|", req_text, re.M))
    normative_packages = set(re.findall(r"^\| (P\d+\.\d+)\s", plan_text, re.M))
    normative_phases = set(re.findall(r"^### (P\d+) —", plan_text, re.M))
    decision_ids = set(re.findall(r"\bADR-\d{3}\b", adr_text))
    campaign_ids = set(re.findall(r"\| (Q\d+) —", req_text))
    criterion_ids = set(re.findall(r"\bG\d{2}\.\d{2}\b", gate_text))
    require(set(requirements) == normative_requirements, "Register requirements differ from normative register")
    require(set(packages) == normative_packages, "Register packages differ from phase plan")
    require(set(phases) == normative_phases, "Register phases differ from phase plan")
    require(set(gates) == {p["gate_id"] for p in phases.values()}, "Phase/gate mapping mismatch")
    for phase in phases.values():
        pid = phase["id"]
        require(set(phase["dependency_phase_ids"]) <= set(phases), f"Unknown dependency for {pid}")
        require(set(phase["package_ids"]) == {p["id"] for p in packages.values() if p["phase_id"] == pid}, f"Package membership mismatch for {pid}")
        require(gates.get(phase["gate_id"], {}).get("phase_id") == pid, f"Gate phase mismatch for {pid}")
    for package in packages.values():
        pid = package["id"]
        require(package["phase_id"] in phases, f"Unknown package phase: {pid}")
        require(set(package.get("dependency_package_ids", [])) <= set(packages), f"Unknown package dependency: {pid}")
        require(set(package.get("criterion_ids", [])) <= criterion_ids, f"Unknown package criterion: {pid}")
        for path in package.get("doc_refs", []):
            require((ROOT / path).is_file(), f"Missing package document: {pid}: {path}")
    # Detect a cycle in the phase dependency graph.
    active, done = set(), set()
    def visit(pid):
        if pid in active:
            errors.append(f"Phase dependency cycle at {pid}")
            return
        if pid in done or pid not in phases:
            return
        active.add(pid)
        for dependency in phases[pid]["dependency_phase_ids"]:
            visit(dependency)
        active.remove(pid)
        done.add(pid)
    for pid in phases:
        visit(pid)
    used_packages = set()
    for req in requirements.values():
        rid = req["id"]
        used_packages.update(req["package_ids"])
        for key, valid in (("package_ids", packages), ("phase_ids", phases), ("gate_ids", gates), ("decision_ids", decision_ids), ("campaign_ids", campaign_ids)):
            require(set(req[key]) <= set(valid), f"Unknown {key} in {rid}")
        for path in req["contract_refs"]:
            require((ROOT / path).is_file(), f"Missing specification {path} in {rid}")
    require(used_packages == set(packages), "Some packages have no requirement mapping: " + ", ".join(sorted(set(packages) - used_packages)))
    for kind in ("phases", "work_packages", "requirements"):
        for record in collections[kind].values():
            rid, status = record["id"], record.get("status", {})
            require(set(status) == set(STATUS), f"Missing/extra status axes in {rid}")
            for axis, value in status.items():
                require(value in STATUS.get(axis, set()), f"Invalid {axis}={value} in {rid}")
                if value == "NOT_APPLICABLE_REVIEWED":
                    review = record.get("applicability_review", {}).get(axis, {})
                    require(all(review.get(k) for k in ("reason", "reviewer", "date", "scope")), f"Missing applicability review for {rid}/{axis}")
            require(set(record["evidence_ids"]) <= set(evidence), f"Unknown evidence in {rid}")
            require(set(record["blocker_ids"]) <= set(blockers), f"Unknown blocker in {rid}")
            if any(v in {"COMPLETE", "PASSED", "QUALIFIED", "ACCEPTED"} for v in status.values()):
                require(bool(record["evidence_ids"]), f"Positive status has no evidence: {rid}")
            if status.get("native_qualification") == "QUALIFIED":
                require(any(evidence.get(e, {}).get("level") == "E3" for e in record["evidence_ids"]), f"No E3 evidence for {rid}")
            if status.get("operational_acceptance") == "ACCEPTED":
                require(any(evidence.get(e, {}).get("level") == "E4" for e in record["evidence_ids"]), f"No E4 evidence for {rid}")
    for gate in gates.values():
        require(gate["decision"] in GATE_VALUES, f"Invalid gate decision: {gate['id']}")
        require(set(gate["evidence_ids"]) <= set(evidence), f"Unknown gate evidence: {gate['id']}")
        require(set(gate["blocker_ids"]) <= set(blockers), f"Unknown gate blocker: {gate['id']}")
        if gate["decision"] in {"PASSED", "FAILED"}:
            require(bool(gate["reviewer"] and gate["reviewed_at"] and gate["evidence_ids"]), f"Unsubstantiated gate review: {gate['id']}")
    evidence_fields = {"id", "level", "artifact_uri", "sha256", "source_revision", "artifact_revisions", "environment", "scope", "campaign_ids", "criterion_ids", "observed_at", "observer", "reviewer", "limitations", "valid_until", "invalidated_at"}
    for record in evidence.values():
        eid = record["id"]
        require(evidence_fields <= set(record), f"Missing evidence metadata: {eid}")
        require(record.get("level") in {"E0", "E1", "E2", "E3", "E4"}, f"Invalid evidence level: {eid}")
        require(bool(re.fullmatch(r"[0-9a-fA-F]{64}", record.get("sha256", ""))), f"Invalid evidence digest: {eid}")
        require(set(record.get("campaign_ids", [])) <= campaign_ids, f"Unknown campaign: {eid}")
        require(set(record.get("criterion_ids", [])) <= criterion_ids, f"Unknown criterion: {eid}")
        if record.get("level") == "E3":
            require(bool(record.get("qualification_tuple") and record.get("campaign_authorization_ref")), f"Missing native scope/authority: {eid}")
    scope_ids = set(phases) | set(packages) | set(requirements) | set(gates)
    for record in blockers.values():
        require(set(record.get("scope_ids", [])) <= scope_ids, f"Unknown blocker scope: {record['id']}")
        require(record.get("state") in {"OPEN", "RESOLVED"}, f"Invalid blocker state: {record['id']}")
        for key in ("owner_role", "description", "unblock_condition", "next_action"):
            require(bool(record.get(key)), f"Missing blocker {key}: {record['id']}")

    markdown_files = sorted(ROOT.rglob("*.md"))
    for path in markdown_files:
        content = path.read_text()
        fences = re.findall(r"^\s*(`{3,}|~{3,})", content, re.M)
        require(len(fences) % 2 == 0, f"Unclosed Markdown fence: {path.relative_to(ROOT)}")
        # Remove fenced examples before validating authored local links.
        prose = re.sub(r"^\s*```[^\n]*\n.*?^\s*```\s*$", "", content, flags=re.M | re.S)
        for link in re.findall(r"\]\(([^)]+)\)", prose):
            target = link.split(' "', 1)[0]
            parts = urlsplit(target)
            if parts.scheme or target.startswith("#") or not parts.path:
                continue
            resolved = (path.parent / unquote(parts.path)).resolve()
            require(resolved.is_relative_to(ROOT), f"Link escapes repository: {path.relative_to(ROOT)} → {target}")
            require(resolved.exists(), f"Broken local link: {path.relative_to(ROOT)} → {target}")
    for path, expected in render_views(register).items():
        require(path.exists() and path.read_text() == expected, f"Stale generated view: {path.relative_to(ROOT)}")
    if errors:
        for error in errors:
            print("ERROR:", error, file=sys.stderr)
        return 1
    print(f"Validated {len(markdown_files)} Markdown documents; {len(phases)} phases, {len(packages)} packages, {len(requirements)} requirements and {len(gates)} gates. Views, local links, IDs and status/evidence references are consistent.")
    print("This checks repository documentation only; no product behavior or native outcome is verified.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(validate())
    except (KeyError, TypeError, ValueError, yaml.YAMLError) as exc:
        print(f"ERROR: malformed delivery register: {exc}", file=sys.stderr)
        sys.exit(1)
