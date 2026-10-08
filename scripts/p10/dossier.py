"""Freeze candidate source and reconcile P10 evidence; never grant release authority."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from evidence import (
    Held,
    bounded_file,
    canonical,
    decode,
    digest,
    number,
    reference,
    referenced_bytes,
    require,
    sha256,
    timestamp,
)

ROOT = Path(__file__).resolve().parents[2]
PREFIXES = (
    "apps/",
    "services/",
    "workers/",
    "contracts/",
    "deploy/",
    "architecture/",
    "scripts/",
    ".github/",
    "release/",
    "docs/engineering/",
    "docs/decisions/",
    "docs/operations/",
    "docs/qualification/",
    "docs/releases/",
    "docs/implementation/phases/",
    "docs/implementation/gates.md",
    "docs/implementation/support-matrix.md",
)
ROOT_INPUTS = {"requirements-docs.txt", ".gitignore", ".gitattributes", "CONTRIBUTING.md"}
CASES = {
    "P10.01": ["Q10.01", "Q10.02", "Q10.03", "Q10.04", "Q10.05", "Q09.06"],
    "P10.02": ["Q09.04", "Q09.05", "Q09.07", "Q09.08", "Q09.11", "Q09.12"],
    "P10.03": ["Q09.02", "Q09.03", "Q09.09", "Q09.13", "Q09.14"],
    "P10.04": ["Q10.06", "Q10.07", "Q10.09"],
    "P10.05": ["Q09.01", "Q09.09", "Q09.10", "Q09.13"],
    "P10.06": ["Q10.10"],
}


def candidate_digest(candidate):
    # Commit provenance is retained but is not executable content. An evidence-only
    # commit must not invalidate the very candidate to which its reports refer.
    return digest(
        canonical(
            {
                k: v
                for k, v in candidate.items()
                if k not in {"candidate_sha256", "source_revision"}
            }
        )
    )


def freeze(root=ROOT):
    def git(*args):
        return subprocess.check_output(["git", *args], cwd=root)

    require(
        not git("status", "--porcelain", "--untracked-files=normal").strip(),
        "candidate_checkout_dirty",
    )
    source = git("rev-parse", "HEAD").decode().strip()
    entries = git("ls-files", "--stage", "-z").decode().rstrip("\0").split("\0")
    modes = {}
    for entry in entries:
        metadata, path = entry.split("\t", 1)
        mode, _, stage = metadata.split()
        if (
            not (path.startswith(PREFIXES) or path in ROOT_INPUTS)
            or path == "release/p10-inputs.json"
        ):
            continue
        require(
            stage == "0" and mode in {"100644", "100755"},
            "unsupported_candidate_source",
        )
        modes[path] = mode
    # Input/review packets are separately hashed; never include a candidate's own digest in its hash.
    bindings = {p: digest(bounded_file(root, p)) for p in modes}
    value = {
        "schema_version": 2,
        "source_revision": source,
        "source_bindings": bindings,
        "source_modes": modes,
        "component_registry_sha256": digest(
            bounded_file(root, "deploy/build/components.json")
        ),
    }
    value["candidate_sha256"] = candidate_digest(value)
    return value


def reviewed_input_digest(packet):
    return digest(
        canonical({k: v for k, v in packet.items() if k != "receiving_reviews"})
    )


def reconcile(root, candidate, packet, *, source_root=None):
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
        type(packet["schema_version"]) is int and packet["schema_version"] == 2,
        "invalid_p10_version",
    )
    expected = candidate["candidate_sha256"]
    require(
        set(candidate)
        == {
            "schema_version",
            "source_revision",
            "source_bindings",
            "source_modes",
            "component_registry_sha256",
            "candidate_sha256",
        }
        and type(candidate["schema_version"]) is int
        and candidate["schema_version"] == 2
        and isinstance(candidate["source_revision"], str)
        and re.fullmatch(r"[a-f0-9]{40}", candidate["source_revision"]) is not None
        and isinstance(candidate["source_bindings"], dict)
        and bool(candidate["source_bindings"])
        and all(
            isinstance(p, str) and sha256(s)
            for p, s in candidate["source_bindings"].items()
        )
        and isinstance(candidate["source_modes"], dict)
        and set(candidate["source_modes"]) == set(candidate["source_bindings"])
        and all(
            mode in {"100644", "100755"} for mode in candidate["source_modes"].values()
        )
        and candidate["component_registry_sha256"]
        == candidate["source_bindings"].get("deploy/build/components.json")
        and sha256(expected)
        and candidate_digest(candidate) == expected,
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
                isinstance(document["approved_by"], str)
                and document["approved_by"].strip()
                and isinstance(document["targets"], dict)
                and document["targets"]
                and isinstance(document["scope"], dict)
                and document["scope"],
                "unapproved_workload_model",
            )
            timestamp(document["approved_at"])
            for target in document["targets"].values():
                number(target)
        elif key == "artifact_set":
            registry_bytes = bounded_file(
                source_root or root, "deploy/build/components.json"
            )
            require(
                digest(registry_bytes) == candidate["component_registry_sha256"],
                "candidate_registry_changed",
            )
            registry = decode(registry_bytes)
            identities = {
                "image_sha256",
                "lock_sha256",
                "sbom_sha256",
                "provenance_sha256",
                "signature_sha256",
                "trust_root_sha256",
            }
            require(
                isinstance(document["components"], dict)
                and set(document["components"])
                == {c["id"] for c in registry["components"]}
                and all(
                    isinstance(row, dict)
                    and set(row) == identities
                    and all(sha256(s) for s in row.values())
                    for row in document["components"].values()
                )
                and document["trust_verification"] == "PASSED"
                and document["restricted_install"] == "PASSED",
                "candidate_artifact_set_incomplete",
            )
        elif key == "security_findings":
            require(
                document["verification_standard"]
                and document["applicability_review"]
                and document["open_required_findings"] == []
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
                and timestamp(document["acknowledged_at"])
                >= timestamp(document["delivered_at"]),
                "operations_receipt_incomplete",
            )
    observations = {}
    require(isinstance(packet["evidence"], list), "invalid_evidence_set")
    for ref in packet["evidence"]:
        report = reference(root, ref)
        require(
            isinstance(report, dict)
            and set(report)
            == {
                "case_id",
                "candidate_sha256",
                "source_bindings",
                "tuple_digests",
                "native_write_authorized",
                "result",
                "checks",
                "failed",
                "errors",
                "skipped",
                "evidence_level",
                "environment",
                "observations",
                "observed_at",
                "observer_id",
                "scope",
            },
            "invalid_case_report",
        )
        require(
            report["case_id"] in {c for cases in CASES.values() for c in cases},
            "unknown_case",
        )
        require(
            all(
                type(report[k]) is int and report[k] >= 0
                for k in ("checks", "failed", "errors", "skipped")
            )
            and report["checks"] > 0
            and sum(report[k] for k in ("failed", "errors", "skipped"))
            <= report["checks"],
            "invalid_case_counts",
        )
        require(
            isinstance(report["observer_id"], str)
            and bool(report["observer_id"].strip())
            and isinstance(report["scope"], dict)
            and bool(report["scope"])
            and isinstance(report["observations"], list)
            and bool(report["observations"]),
            "case_observations_missing",
        )
        timestamp(report["observed_at"])
        for original in report["observations"]:
            require(
                bool(referenced_bytes(root, original)), "empty_original_observation"
            )
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
            and review["candidate_sha256"] == expected
            and review["reviewed_input_sha256"] == reviewed_input_digest(packet),
            "ambiguous_or_changed_review",
        )
        timestamp(review["reviewed_at"])
        require(
            all(
                isinstance(review[k], str) and review[k].strip()
                for k in ("reviewer_id", "implementer_id")
            ),
            "invalid_review_identity",
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
                or row["errors"]
                or row["skipped"]
                or row["evidence_level"]
                not in ({"E4"} if minimum == "E4" else {"E3", "E4"})
                or row["environment"]
                not in (
                    {"representative_preproduction", "operational_review"}
                    if minimum == "E4"
                    else {"representative_preproduction", "qualified_native_lab"}
                )
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
            or not review["implementer_id"]
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
        "schema_version": 2,
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
    parser.add_argument(
        "--evidence-root",
        type=Path,
        default=ROOT,
        help="Root of the protected local evidence bundle; may be outside Git",
    )
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    try:
        candidate = freeze()
        packet = decode(bounded_file(args.input.absolute().parent, args.input.name))
        result = reconcile(args.evidence_root, candidate, packet, source_root=ROOT)
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
