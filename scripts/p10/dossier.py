"""Freeze candidate source and reconcile P10 evidence; never grant release authority."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from evidence import Held, bounded_file, canonical, decode, digest, reference, require

ROOT = Path(__file__).resolve().parents[2]
PREFIXES = (
    "apps/",
    "services/",
    "workers/",
    "contracts/",
    "deploy/",
    "architecture/",
    "scripts/",
    ".github/workflows/",
    "release/",
)
CASES = {
    "P10.01": ["Q10.01", "Q10.02", "Q10.03", "Q10.04", "Q10.05", "Q09.06"],
    "P10.02": ["Q09.04", "Q09.05", "Q09.07", "Q09.08", "Q09.11", "Q09.12"],
    "P10.03": ["Q09.02", "Q09.03", "Q09.09", "Q09.13", "Q09.14"],
    "P10.04": ["Q10.06", "Q10.07", "Q10.09"],
    "P10.05": ["Q09.01", "Q09.09", "Q09.10", "Q09.13"],
    "P10.06": ["Q10.10"],
}


def freeze(root=ROOT):
    def git(*args):
        return subprocess.check_output(["git", *args], cwd=root)

    require(
        not git("status", "--porcelain", "--untracked-files=normal").strip(),
        "candidate_checkout_dirty",
    )
    source = git("rev-parse", "HEAD").decode().strip()
    paths = git("ls-files", "-z").decode().rstrip("\0").split("\0")
    # Input/review packets are separately hashed; never include a candidate's own digest in its hash.
    bindings = {
        p: digest(bounded_file(root, p))
        for p in paths
        if p.startswith(PREFIXES) and p != "release/p10-inputs.json"
    }
    value = {
        "schema_version": 1,
        "source_revision": source,
        "source_bindings": bindings,
        "component_registry_sha256": digest(
            bounded_file(root, "deploy/build/components.json")
        ),
    }
    value["candidate_sha256"] = digest(canonical(value))
    return value


def reconcile(root, candidate, packet):
    require(
        set(packet)
        == {
            "schema_version",
            "candidate_sha256",
            "selected_tuples",
            "prerequisite_reviews",
            "workload_model",
            "artifact_set",
            "security_findings",
            "operating_receipts",
            "evidence",
            "receiving_reviews",
        },
        "invalid_p10_packet",
    )
    require(
        type(packet["schema_version"]) is int and packet["schema_version"] == 1,
        "invalid_p10_version",
    )
    expected = candidate["candidate_sha256"]
    require(
        digest(
            canonical({k: v for k, v in candidate.items() if k != "candidate_sha256"})
        )
        == expected,
        "candidate_digest_changed",
    )
    holds = []
    if packet["candidate_sha256"] != expected:
        holds.append("candidate_not_bound")
    tuples = packet["selected_tuples"]
    require(
        isinstance(tuples, list)
        and len(tuples) == len(set(tuples))
        and all(isinstance(t, str) and re.fullmatch("[a-f0-9]{64}", t) for t in tuples),
        "invalid_release_tuples",
    )
    if not tuples:
        holds.append("qualified_release_tuples_not_selected")
    for key in (
        "prerequisite_reviews",
        "workload_model",
        "artifact_set",
        "security_findings",
        "operating_receipts",
    ):
        if packet[key] is None:
            holds.append(key + "_missing")
            continue
        document = reference(root, packet[key])
        require(document["candidate_sha256"] == expected, key + "_candidate_changed")
        if key == "prerequisite_reviews":
            require(
                set(document["gates"]) == {"G07", "G08", "G09"}
                and all(v == "ACCEPTED" for v in document["gates"].values())
                and set(document["tuple_digests"]) == set(tuples),
                "prerequisite_review_incomplete",
            )
        elif key == "workload_model":
            require(
                document["approved_by"]
                and document["approved_at"]
                and document["targets"]
                and document["scope"],
                "unapproved_workload_model",
            )
        elif key == "artifact_set":
            registry = decode(bounded_file(root, "deploy/build/components.json"))
            require(
                set(document["components"]) == {c["id"] for c in registry["components"]}
                and document["trust_verification"] == "PASSED"
                and document["restricted_install"] == "PASSED",
                "candidate_artifact_set_incomplete",
            )
        elif key == "security_findings":
            require(
                document["verification_standard"]
                and document["applicability_review"]
                and not document["open_required_findings"]
                and document["custody_review"],
                "security_findings_open",
            )
        else:
            require(
                document["receiving_owner"]
                and document["support_scope"]
                and document["retention_review"]
                and document["incident_id"]
                and document["alert_id"]
                and document["acknowledged_at"] >= document["delivered_at"],
                "operations_receipt_incomplete",
            )
    observations = {}
    require(isinstance(packet["evidence"], list), "invalid_evidence_set")
    for ref in packet["evidence"]:
        report = reference(root, ref)
        require(report["case_id"] not in observations, "duplicate_case_observation")
        require(
            report["candidate_sha256"] == expected
            and report["source_bindings"] == candidate["source_bindings"],
            "evidence_requires_candidate_rerun",
        )
        require(
            report["tuple_digests"] == tuples
            and report["native_write_authorized"] is False,
            "evidence_scope_or_authority_changed",
        )
        # Failed/skipped originals remain recorded but cannot satisfy a required criterion.
        observations[report["case_id"]] = report
    reviews = {}
    require(isinstance(packet["receiving_reviews"], list), "invalid_receiving_reviews")
    for ref in packet["receiving_reviews"]:
        review = reference(root, ref)
        require(
            review["package_id"] in CASES
            and review["package_id"] not in reviews
            and review["candidate_sha256"] == expected,
            "ambiguous_or_changed_review",
        )
        reviews[review["package_id"]] = review
    packages = []
    for package, cases in CASES.items():
        reasons = []
        for case in cases:
            row = observations.get(case)
            minimum = "E4" if package in {"P10.04", "P10.06"} else "E3"
            if row is None:
                reasons.append(case + ":not_run")
            elif (
                row["result"] != "PASSED"
                or row["failed"]
                or row["skipped"]
                or row["evidence_level"]
                not in ({"E4"} if minimum == "E4" else {"E3", "E4"})
                or row["environment"]
                not in {
                    "representative_preproduction",
                    "qualified_native_lab",
                    "operational_review",
                }
            ):
                reasons.append(
                    case + ":required_native_or_operational_evidence_missing"
                )
        review = reviews.get(package)
        if (
            not review
            or review["decision"] != "ACCEPTED"
            or not review["reviewed_at"]
            or not review["reviewer_id"]
            or review["reviewer_id"] == review["implementer_id"]
        ):
            reasons.append("independent_receiving_review_missing")
        packages.append(
            {
                "id": package,
                "status": "HELD" if reasons or holds else "PACKET_COMPLETE",
                "holds": reasons,
            }
        )
    return {
        "schema_version": 1,
        "candidate_sha256": expected,
        "source_revision": candidate["source_revision"],
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "input_sha256": digest(canonical(packet)),
        "status": "HELD"
        if holds or any(p["holds"] for p in packages)
        else "PACKET_COMPLETE_REQUIRES_AUTHENTICITY_REVIEW",
        "holds": holds,
        "packages": packages,
        "evidence_authenticity_established": False,
        "release_authorized": False,
        "native_write_authorized": False,
        "limitations": [
            "Offline hashes establish byte integrity only; reviewers and receipts require independent authentication.",
            "E1/E2 software checks cannot satisfy G10 native or operating acceptance.",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=ROOT / "release/p10-inputs.json")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    try:
        candidate = freeze()
        packet = decode(args.input.read_bytes())
        result = reconcile(ROOT, candidate, packet)
        (args.output / "candidate.json").write_bytes(canonical(candidate) + b"\n")
        (args.output / "dossier.json").write_bytes(canonical(result) + b"\n")
        print(
            json.dumps(
                {
                    "status": result["status"],
                    "candidate_sha256": candidate["candidate_sha256"],
                    "release_authorized": False,
                }
            )
        )
        return 2 if result["status"] == "HELD" else 0
    except (Held, ValueError, KeyError, TypeError, OSError) as error:
        (args.output / "dossier.json").write_bytes(
            canonical(
                {"status": "INVALID", "release_authorized": False, "error": str(error)}
            )
            + b"\n"
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
