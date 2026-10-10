"""Validate the cross-platform mapping against every field in its source manifest.

This check is independent of native discovery and never qualifies an API,
adapter, feature, installed environment or migration plan.
"""

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
PLATFORMS = ("vmware", "ahv", "openstack")
MANIFEST = ROOT / "contracts/capabilities/migration-collection-manifest-v1.json"
CROSSWALK = ROOT / "contracts/capabilities/migration-field-crosswalk-v1.json"


def load(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("invalid_crosswalk_json")
    return data


def fail(reason: str) -> None:
    raise ValueError(reason)


def validate(
    source: dict[str, Any], crosswalk: dict[str, Any]
) -> dict[str, int]:
    if (
        crosswalk.get("schema_version") != 1
        or crosswalk.get("crosswalk_version") != "1.0.0"
        or crosswalk.get("status") != "declared_mapping_not_native_evidence"
        or crosswalk.get("collection_manifest")
        != "contracts/capabilities/migration-collection-manifest-v1.json"
    ):
        fail("invalid_crosswalk_identity")
    definitions = {
        p: {row["id"]: row for row in source["platforms"][p]["attributes"]}
        for p in PLATFORMS
    }
    if any(
        len(definitions[p]) != len(source["platforms"][p]["attributes"])
        for p in PLATFORMS
    ):
        fail("source_manifest_duplicate_field")
    fields = crosswalk.get("fields")
    if not isinstance(fields, list) or not fields:
        fail("crosswalk_fields_required")
    used = {p: set() for p in PLATFORMS}
    canonical = set()
    shared = single = owner = 0
    for row in fields:
        if not isinstance(row, dict):
            fail("invalid_crosswalk_row")
        key = row.get("canonical_id")
        if not isinstance(key, str) or key in canonical:
            fail("crosswalk_canonical_duplicate")
        canonical.add(key)
        scope = row.get("scope")
        if scope not in {"source", "target", "owner"} or not key.startswith(scope + "."):
            fail("crosswalk_scope_changed")
        relation = row.get("relationship")
        if relation not in {"normalize", "conditional", "platform_specific", "owner_common"}:
            fail("crosswalk_semantics_invalid")
        if row.get("qualification") != "not_qualified":
            fail("crosswalk_cannot_assert_qualification")
        if row.get("migration_policy") != (
            "owner_evidence_required" if relation == "owner_common"
            else "independent_qualification_required"
        ):
            fail("crosswalk_migration_policy_invalid")
        if not isinstance(row.get("semantic_constraints"), str) or len(
            row["semantic_constraints"]
        ) < 25:
            fail("crosswalk_semantic_warning_required")
        platforms = row.get("platforms")
        if not isinstance(platforms, dict) or set(platforms) != set(PLATFORMS):
            fail("crosswalk_platforms_required")
        active = 0
        max_severity = "optional"
        youngest = 86400
        for platform in PLATFORMS:
            mapping = platforms[platform]
            if mapping is None:
                continue
            if not isinstance(mapping, dict):
                fail("crosswalk_mapping_invalid")
            ids = mapping.get("manifest_attribute_ids")
            if (
                not isinstance(ids, list)
                or not ids
                or len(set(ids)) != len(ids)
                or any(not isinstance(i, str) for i in ids)
            ):
                fail("crosswalk_field_references_invalid")
            records = []
            for field in ids:
                if field not in definitions[platform] or field in used[platform]:
                    fail("crosswalk_field_missing_or_repeated")
                used[platform].add(field)
                record = definitions[platform][field]
                if record["scope"] != scope:
                    fail("crosswalk_source_target_scope_changed")
                records.append(record)
            # All provenance and freshness must be copied from the same
            # source manifest; never substitute a guessed vendor field.
            if (
                mapping.get("api_fields") != [x["api_field"] for x in records]
                or mapping.get("owner_evidence_fields")
                != [x["owner_evidence_field"] for x in records]
                or mapping.get("methods") != [x["collection_method"] for x in records]
                or mapping.get("max_age_seconds")
                != min(x["max_age_seconds"] for x in records)
                or mapping.get("severity")
                != (
                    "critical" if any(x["severity"] == "critical" for x in records)
                    else "optional"
                )
                or set(mapping.get("conditions", []))
                != {x["condition"] for x in records}
            ):
                fail("crosswalk_source_binding_changed")
            if mapping["severity"] == "critical":
                max_severity = "critical"
            youngest = min(youngest, mapping["max_age_seconds"])
            active += 1
        if active == 0:
            fail("crosswalk_empty_row")
        if (row.get("criticality"), row.get("maximum_age_seconds")) != (
            max_severity, youngest
        ):
            fail("crosswalk_criticality_or_freshness_downgrade")
        if relation == "platform_specific" and active != 1:
            fail("crosswalk_platform_specific_not_single")
        if relation == "owner_common":
            if scope != "owner" or active != len(PLATFORMS):
                fail("crosswalk_owner_scope_invalid")
            owner += 1
        if active == len(PLATFORMS):
            shared += 1
        else:
            single += 1
    for platform in PLATFORMS:
        if used[platform] != set(definitions[platform]):
            fail("crosswalk_manifest_fields_uncovered")
    summary = crosswalk.get("summary", {})
    if (
        summary.get("groups") != len(fields)
        or summary.get("shared_columns") != shared
        or summary.get("partial_columns") != single
        or summary.get("owner_common") != owner
        or summary.get("platform_specific")
        != sum(row["relationship"] == "platform_specific" for row in fields)
    ):
        fail("crosswalk_summary_drift")
    for platform in PLATFORMS:
        if summary.get("manifest_fields", {}).get(platform) != {
            "matched": len(used[platform]), "total": len(definitions[platform])
        }:
            fail("crosswalk_coverage_summary_drift")
    return {"fields": sum(len(used[p]) for p in PLATFORMS), "groups": len(fields)}


if __name__ == "__main__":
    result = validate(load(MANIFEST), load(CROSSWALK))
    print(f"Cross-platform VM field mapping valid: {result['fields']} fields in "
          f"{result['groups']} canonical groups; native support is unverified")
