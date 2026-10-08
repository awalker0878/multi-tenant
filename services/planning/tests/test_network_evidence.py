"""A07/A08: equality and boolean declarations cannot replace measured native controls."""

from copy import deepcopy

from planning_fixture import NOW, inputs

from planning.domain.network_evidence import isolation_checks, network_checks


def test_missing_route_and_failed_negative_control_block() -> None:
    intent, destination, _, policy, _ = inputs()
    data = destination["capability_snapshot"]["data"]
    assert all(s == "eligible" for _, s, _, _ in network_checks(intent, data, policy, NOW))
    missing = deepcopy(data)
    missing["network"]["topology"]["routes"] = []
    from planning.domain.model import digest

    missing["network"]["topology_sha256"] = digest(missing["network"]["topology"])
    assert any(s != "eligible" for _, s, _, _ in network_checks(intent, missing, policy, NOW))
    failed = deepcopy(data)
    failed["network"]["measurements"][-1]["outcome"] = "allow"
    assert any(
        s == "blocked" for _, s, _, _ in isolation_checks(intent, destination, failed, policy, NOW)
    )


def test_domain_aliasing_and_same_observer_writer_are_rejected() -> None:
    intent, destination, _, policy, _ = inputs()
    data = destination["capability_snapshot"]["data"]
    domains = data["isolation"]["domains"]
    names = list(domains)
    domains[names[1]] = domains[names[0]]
    data["isolation"]["observer_principal"] = data["isolation"]["writer_principal"]
    assert all(
        s == "blocked" for _, s, _, _ in isolation_checks(intent, destination, data, policy, NOW)
    )
