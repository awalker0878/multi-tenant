#!/usr/bin/env python3
"""Render documentation views without changing canonical delivery state."""

import argparse
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
REGISTER = ROOT / "docs/implementation/delivery-register.yaml"
AXES = ("work", "verification", "native_qualification", "operational_acceptance")


def cell(value):
    if isinstance(value, list):
        value = ", ".join(str(item) for item in value) or "—"
    return str(value if value is not None else "—").replace("|", "\\|").replace("\n", " ")


def table(headers, rows):
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
    lines.extend("| " + " | ".join(cell(value) for value in row) + " |" for row in rows)
    return "\n".join(lines)


def render_views(register):
    phases = register["phases"]
    packages = register["work_packages"]
    requirements = register["requirements"]
    gates = {record["id"]: record for record in register["gates"]}
    preamble = (
        "Generated from [delivery-register.yaml](delivery-register.yaml). "
        "Edit the register and run `python scripts/render_delivery_views.py` from the repository root. "
        "Do not edit this view independently.\n\n"
        "Status meanings and review rules are in [status-model.md](status-model.md). "
        "Empty evidence fields mean no reviewed evidence has been registered; document existence is not implementation.\n"
    )
    progress = ["# Delivery progress\n", preamble, f"Baseline: {register['baseline_date']}. Branch: `{register['branch']}`.\n"]
    progress.append("## Phases\n")
    progress.append(table(
        ["Phase", "Outcome", "Work", "Verification", "Native qualification", "Operating acceptance", "Gate", "Evidence / blockers"],
        [[p["id"], p["title"], *(p["status"][a] for a in AXES),
          f"{p['gate_id']}: {gates[p['gate_id']]['decision']}",
          f"{len(p['evidence_ids'])} / {len(p['blocker_ids'])}"] for p in phases]
    ))
    progress.append("\n## Packages\n\nPackage state is independent of phase roll-up. Detailed work appears in the [phase documents](phases/README.md); review each specification against current decisions and evidence before implementation.\n")
    progress.append(table(
        ["Package", "Output", "Owner role", "Work", "Verification", "Native qualification", "Operating acceptance", "Evidence / blockers"],
        [[p["id"], p["title"], p["owner_role"], *(p["status"][a] for a in AXES),
          f"{len(p['evidence_ids'])} / {len(p['blocker_ids'])}"] for p in packages]
    ))
    progress.append("\n## Registered evidence and blockers\n")
    progress.append(f"Evidence records: **{len(register['evidence'])}**. Blocker records: **{len(register['blockers'])}**. Planning inputs awaiting selection are described in the phase cards; an empty blocker register does not mean those inputs are already available.\n")
    if register["evidence"]:
        progress.append(table(["ID", "Level", "Environment", "Revision", "Limitations"],
                              [[e["id"], e["level"], e["environment"], e["source_revision"], e["limitations"]] for e in register["evidence"]]))
    if register["blockers"]:
        progress.append(table(["ID", "Scope", "Owner", "State", "Unblock condition", "Next action"],
                              [[b["id"], b["scope_ids"], b["owner_role"], b["state"], b["unblock_condition"], b["next_action"]] for b in register["blockers"]]))

    trace = ["# Requirement traceability\n", preamble,
             "Requirement wording and campaigns are owned by [requirements-and-qualification.md](requirements-and-qualification.md). "
             "Contracts below link to candidate specifications, not implemented API schemas. "
             "Gate criteria are in [gates.md](gates.md).\n", "## Requirement mapping\n"]
    def doc_link(path):
        return f"[{Path(path).stem}](../../{path})"
    trace.append(table(
        ["Requirement", "Packages", "Decisions", "Contract / service specifications", "Campaigns", "Gates"],
        [[r["id"], r["package_ids"], r["decision_ids"], ", ".join(doc_link(p) for p in r["contract_refs"]), r["campaign_ids"], r["gate_ids"]] for r in requirements]
    ))
    trace.append("\n## Requirement state\n")
    trace.append(table(
        ["Requirement", "Work", "Verification", "Native qualification", "Operating acceptance", "Evidence", "Blockers"],
        [[r["id"], *(r["status"][a] for a in AXES), r["evidence_ids"], r["blocker_ids"]] for r in requirements]
    ))
    trace.append("\n## Package coverage\n\nDerived from the canonical requirement-to-package mappings. A package with no linked requirement needs review.\n")
    trace.append(table(["Package", "Requirements"],
                       [[p["id"], [r["id"] for r in requirements if p["id"] in r["package_ids"]]] for p in packages]))
    return {
        ROOT / "docs/implementation/progress.md": "\n".join(progress).rstrip() + "\n",
        ROOT / "docs/implementation/traceability.md": "\n".join(trace).rstrip() + "\n",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Report stale views without writing")
    args = parser.parse_args()
    register = yaml.safe_load(REGISTER.read_text())
    stale = []
    for path, content in render_views(register).items():
        if not path.exists() or path.read_text() != content:
            stale.append(str(path.relative_to(ROOT)))
            if not args.check:
                path.write_text(content)
    if args.check and stale:
        parser.exit(1, "Stale views: " + ", ".join(stale) + "\n")
    print("Delivery views are current." if args.check else "Rendered progress and traceability from the delivery register.")


if __name__ == "__main__":
    main()
