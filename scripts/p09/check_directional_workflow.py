"""Cross-owner directional admission and recovery conformance with synthetic owners.

Run from the Planning locked environment. Concrete worker dispatch is exercised by
test_method_protocol and the platform adapter suites; this checks that their exact
direction/artifact requirements survive Planning -> Lifecycle composition. It
does not claim an installed platform, application owner or guest is qualified.
"""

import copy
import itertools
import json
import sys
from pathlib import Path
from unittest.mock import Mock
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [
    str(ROOT / p)
    for p in (
        "services/planning/src",
        "services/planning/tests",
        "services/lifecycle/src",
    )
]

from test_expansion import RETEST, route_for
from test_migration_plans import values

from planning.application.migration_support import METHODS, MigrationSupport
from planning.domain.compilation import bind
from planning.domain.migration_plan import DELTA, compose_migration, stage_order
from planning.domain.model import Actor, Rejected as PlanningHeld, digest
from lifecycle.domain.execution import Rejected as LifecycleHeld
from lifecycle.domain.migration import cases, recovery_matches, stages
from lifecycle.domain.migration_outcomes import requirements
from lifecycle.domain.native_workflow import observations, validate_plan
from lifecycle.infrastructure.native_owners import NativeOwners

PLATFORMS = ("vmware", "openstack", "ahv")
MODES = ("rehearsal", "cutover", "rollback", "forward_recovery", "reverse_recovery", "cleanup")
NOW = 1000


def denied(call, error):
    try:
        call()
    except error:
        return
    raise AssertionError("Unsafe cross-owner admission unexpectedly succeeded")


def resolve(content):
    actor, requester, approver = (str(uuid4()) for _ in range(3))
    content["executor_ids"] = [actor]
    binding = bind(content, str(uuid4()), requester)
    assignment = {
        "tenant_id": binding["tenant_id"],
        "plan_id": binding["plan_id"],
        "plan_revision": 1,
        "plan_digest": binding["digest"],
        "actor_id": actor,
        **{k: str(uuid4()) for k in ("approval_id", "executor_id", "campaign_id", "epoch")},
    }
    # An independently approved synthetic owner record feeds the production resolver.
    config, transport = Mock(), Mock()
    config.load.return_value = {"expires_at": 2000}
    config.assignment.return_value = assignment
    approval = {
        "allowed": True,
        "tenant_id": binding["tenant_id"],
        "actor_id": actor,
        "approval_id": assignment["approval_id"],
        "plan_digest": binding["digest"],
        "authority_use": "native_approval",
        "native_write_authorized": False,
        "evaluated_at": NOW,
        "executor_fingerprint": digest("synthetic executor"),
        "requester_id": requester,
        "approval": {
            "state": "approved",
            "revoked": False,
            "approver_grant_current": True,
            "approver_id": approver,
            "plan_id": binding["plan_id"],
            "plan_revision": 1,
            "plan_digest": binding["digest"],
            "expires_at": 1500,
            "scope": {k: binding[k] for k in ("site_id", "environment", "resource_id")},
        },
    }
    transport.request.side_effect = [
        {"content": content, "binding": binding, "invalidated": False},
        approval,
    ]
    result = NativeOwners(config, transport, lambda: NOW).resolve(binding["tenant_id"], assignment)
    validate_plan(result, NOW)
    return result


def records(plan, stage, phase):
    binding = {"stage": stage, "operation_id": str(uuid4())}
    required = requirements(plan["migration"]["outcomes"])
    observer = str(uuid4())
    rows = [
        {
            "case": name,
            "phase": phase,
            "binding_sha256": digest(binding),
            "intent_digest": plan["intents"][stage],
            "observer_id": observer,
            "observed_at": NOW,
            "expires_at": NOW + 30,
            "outcome": "passed",
            "evidence_sha256": digest([name, binding]),
            "policy_results": {c["id"]: c["expectation"] for c in plan["policy_cases"]}
            if name == "policy_paths"
            else {},
            **({"requirement_sha256": required[name]} if name in required else {}),
        }
        for name in cases(plan, stage, phase)
    ]
    return binding, rows


def main():
    scenarios, stage_boundaries, denied_acceptance, denied_support = 0, 0, 0, 0
    for source, target, method, mode in itertools.product(PLATFORMS, PLATFORMS, DELTA, MODES):
        base, bound, recipe = values(mode, method)
        native_project = (
            "datacenter-1"
            if target == "vmware"
            else uuid4().hex
            if target == "openstack"
            else str(uuid4())
        )
        base["scope"].update(project_id=native_project, native_scope="project:" + native_project)
        recipe["scope"]["project_id"] = native_project
        recipe["base_content_sha256"] = digest(base)
        for side, platform in (("source", source), ("target", target)):
            bound[side]["profile_sha256"] = digest([side, platform, source, target])
        route = route_for(source, target, method=METHODS[method])
        for side in ("source", "target"):
            route[side]["profile_sha256"] = bound[side]["profile_sha256"]
        outcomes = {
            "source_platform": source,
            "target_platform": target,
            "owner_inputs_sha256": bound["owner_inputs_sha256"],
            "guest_profile_sha256": recipe["artifacts"]["guest"],
            "guest": {
                k: digest([target, k])
                for k in ("boot", "drivers", "storage", "network", "identity")
            },
            "services": {
                k: digest([target, k])
                for k in (
                    "ipam",
                    "dns",
                    "identity",
                    "time",
                    "trust",
                    "logging",
                    "monitoring",
                    "backup",
                )
            },
            "security": [
                {
                    "id": "application",
                    "source_rule_sha256": digest([source, "rule"]),
                    "target_rule_sha256": digest([target, "rule"]),
                    "semantics_sha256": digest("expected-traffic"),
                }
            ],
            "datasets": {key: digest([key, "data-integrity"]) for key in bound["datasets"]},
        }
        route.update(
            guest_profile_sha256=recipe["artifacts"]["guest"],
            guest_outcomes_sha256=digest(outcomes["guest"]),
            artifacts_sha256=digest(recipe["artifacts"]),
            services_sha256=digest(outcomes["services"]),
            policy_sha256=digest(outcomes["security"]),
            data_sha256=digest(outcomes["datasets"]),
            recovery_sha256=recipe["artifacts"]["recovery"],
        )
        route["constraints"].update(disk_format="raw", maximum_data_loss_bytes=0)
        outcomes["route_sha256"] = digest(route)
        recipe.update(schema_version=3, outcomes=outcomes)
        recipe["campaign"]["route_sha256"] = digest(route)
        selected = {
            "schema_version": 1,
            "id": str(uuid4()),
            "revision": 1,
            "release_sha256": digest("synthetic-release"),
            "owner_role": "Synthetic commissioning owner",
            "expires_at": 2000,
            "routes": [route],
            "operations": [],
            "retest_triggers": list(RETEST),
            "deferred_directions": [
                a + "->" + b
                for a, b in itertools.product(PLATFORMS, repeat=2)
                if (a, b) != (source, target)
            ],
        }
        proof = {
            "route_sha256": digest(route),
            "tranche_sha256": digest(selected),
            "release_sha256": selected["release_sha256"],
            "level": "E3",
            "decision": "accepted",
            "revoked": False,
            "expires_at": 1800,
            "evidence_sha256": digest("synthetic-E3-owner-record"),
        }
        proofs = [proof]
        actor = Actor(
            base["scope"]["tenant_id"],
            str(uuid4()),
            "plan.read",
            base["scope"]["resource_id"],
            base["scope"]["environment"],
        )
        support = MigrationSupport(lambda *_: selected, lambda *_: proofs, lambda: NOW)
        site = base["scope"]["site_id"]
        support.require(actor, site, bound)
        content = compose_migration(base, bound, recipe, NOW)
        content["native_migration"].update(recipe_id=str(uuid4()), base_plan_id=str(uuid4()))
        migration = content["native_migration"]["migration"]
        support.require(actor, site, migration)
        # One direction's proof neither qualifies its inverse nor supplies E4 acceptance.
        matrix = support.read(actor, site)
        assert len(matrix["directions"]) == 9 and matrix["native_write_authorized"] is False
        assert sum(r["native_qualified"] for d in matrix["directions"] for r in d["routes"]) == 1
        assert not any(
            r["operationally_accepted"] for d in matrix["directions"] for r in d["routes"]
        )
        for changed in (
            {"level": "E2"},
            {"revoked": True},
            {"expires_at": NOW},
            {"route_sha256": digest("other-direction")},
        ):
            proofs[:] = [proof | changed]
            denied(lambda: support.require(actor, site, migration), PlanningHeld)
            denied_support += 1
        proofs[:] = [proof]
        plan = resolve(content)
        assert plan["migration"] == migration
        assert tuple(plan["intents"]) == stages(migration) == stage_order(mode, method)
        assert recovery_matches(migration, copy.deepcopy(migration))
        changed = copy.deepcopy(migration)
        changed["target"]["native_identity_sha256"] = digest("other-environment")
        assert not recovery_matches(migration, changed)
        if mode == "rollback":
            assert "no_target_divergence" in cases(plan, "restore_source", "before")
        if mode in {"forward_recovery", "reverse_recovery"}:
            assert "accepted_target_changes_retained" in cases(plan, "preserve_target", "after")
        for stage in stages(migration):
            for phase in ("before", "after"):
                binding, rows = records(plan, stage, phase)
                assert observations(plan, binding, phase, rows, NOW) == digest(rows)
                stage_boundaries += 1
                if source != "vmware":
                    assert not {"ovf_bound", "snapshot_bound", "snapshot_consolidated"} & {
                        r["case"] for r in rows
                    }
        if mode == "cutover":
            binding, rows = records(plan, "admit_writes", "before")
            required = requirements(outcomes)
            for name in required:
                denied(
                    lambda: observations(
                        plan, binding, "before", [r for r in rows if r["case"] != name], NOW
                    ),
                    LifecycleHeld,
                )
                denied_acceptance += 1
            bad = copy.deepcopy(rows)
            next(r for r in bad if r["case"] == "service_backup")["requirement_sha256"] = digest(
                "unrelated-backup"
            )
            denied(lambda: observations(plan, binding, "before", bad, NOW), LifecycleHeld)
            denied_acceptance += 1
        scenarios += 1
    print(
        json.dumps(
            {
                "scenarios": scenarios,
                "stage_boundaries": stage_boundaries,
                "denied_directional_support": denied_support,
                "denied_partial_acceptance": denied_acceptance,
                "evidence_level": "E2",
                "native_platforms_tested": [],
                "native_write_authorized": False,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
