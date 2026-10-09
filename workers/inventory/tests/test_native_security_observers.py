"""Independent observed members, services, category attachments and traffic probes."""
from unittest.mock import patch
from uuid import uuid4

import pytest

from inventory_worker.infrastructure.ahv_effective_observer import collect as ahv_collect
from inventory_worker.infrastructure.nsx_effective_observer import collect as nsx_collect
from inventory_worker.infrastructure.security_probes import collect as probe_collect
from inventory_worker.infrastructure.native import CollectionFailure
from inventory_worker.infrastructure.profile_digest import fingerprint


def test_nsx_group_member_and_service_apis_are_scoped_and_read_only():
    stream = {
        "kind": "nsx_effective_observer", "domain_id": "d1",
        "credential_file": "/mounted/nsx-independent",
        "separate_observer_credential_verified": True,
        "native_api_qualified": True,
        "group_effective_member_types_verified": True,
        "group_effective_member_types": {"web": ["VirtualMachine"]},
    }
    urls = []
    def exchange(conn, url, headers):
        assert conn is stream
        assert headers == {"Authorization": "Basic observer"}
        urls.append(url)
        if "/members/virtual-machines" in url:
            return {"results": [{
                "id": "realized-vm-1", "state": "REALIZED",
                "compute_ids": ["instanceUuid:some-uuid", "externalId:vm-1"],
            }]}
        return {"results": [{
            "resource_type": "L4PortSetServiceEntry", "l4_protocol": "TCP",
            "destination_ports": ["5432", "443-445"],
        }]}
    with (patch("inventory_worker.infrastructure.nsx_effective_observer.exchange",
                side_effect=exchange),
          patch("inventory_worker.infrastructure.nsx_effective_observer.secret",
                return_value="observer")):
        result = nsx_collect(stream, "d1", ["web"], ["postgres"], lambda: None)
    assert len(urls) == 2
    assert result["groups"]["/infra/domains/d1/groups/web"]["members"] == ["vm-1"]
    assert result["services"]["/infra/services/postgres"]["ports"] == [443, 444, 445, 5432]
    assert result["qualification_level"] == "E3_observation_only"
    assert result["native_write_authorized"] is False


def test_nsx_effective_group_truncated_response_holds():
    stream = {
        "kind": "nsx_effective_observer", "domain_id": "d1",
        "credential_file": "/x",
        "separate_observer_credential_verified": True,
        "native_api_qualified": True,
        "group_effective_member_types_verified": True,
        "group_effective_member_types": {"group": ["VirtualMachine"]},
    }
    with (patch("inventory_worker.infrastructure.nsx_effective_observer.exchange",
                return_value={"results": [], "cursor": "more"}),
          patch("inventory_worker.infrastructure.nsx_effective_observer.secret",
                return_value="observer")):
        with pytest.raises(CollectionFailure, match="incomplete"):
            nsx_collect(stream, "d1", ["group"], [], lambda: None)


def test_nsx_non_vm_group_must_not_look_like_an_empty_vm_group():
    stream = {
        "kind": "nsx_effective_observer", "domain_id": "d1",
        "credential_file": "/x", "native_api_qualified": True,
        "separate_observer_credential_verified": True,
        "group_effective_member_types_verified": True,
        "group_effective_member_types": {"group": ["IPAddress"]},
    }
    with patch("inventory_worker.infrastructure.nsx_effective_observer.secret",
               return_value="observer"):
        with pytest.raises(CollectionFailure, match="member_types_unqualified"):
            nsx_collect(stream, "d1", ["group"], [], lambda: None)


def test_ahv_independent_vm_categories_and_native_nic_ids():
    vm, category, nic = [str(uuid4()) for _ in range(3)]
    stream = {
        "kind": "ahv_effective_observer", "vmm_version": "v4.3",
        "credential_file": "/mounted/prism-independent",
        "separate_observer_credential_verified": True,
        "native_api_qualified": True,
    }
    def exchange(conn, url, headers):
        assert url == "/api/vmm/v4.3/ahv/config/vms/" + vm
        return {"data": {"extId": vm,
                         "categories": [{"extId": category}],
                         "nics": [{"extId": nic}]}}
    with (patch("inventory_worker.infrastructure.ahv_effective_observer.exchange",
                side_effect=exchange),
          patch("inventory_worker.infrastructure.ahv_effective_observer.secret",
                return_value="observer")):
        result = ahv_collect(stream, [vm], lambda: None)
    assert result["vm_categories"][0]["category_ids"] == [category]
    assert result["vm_categories"][0]["native_nic_ids"] == [nic]
    assert "ahv_microseg_attachment_and_service_enforcement_e4_required" in result["holds"]


def test_correlated_probe_requires_native_denial_not_only_timeout():
    probes = [
        {"id": "allowed", "expected": "allow", "source_vm_id": "web",
         "target_vm_id": "db", "protocol": "tcp", "authorized_scope": "test",
         "native_enforcement_point": "gateway"},
        {"id": "forbidden", "expected": "deny", "source_vm_id": "untrusted",
         "target_vm_id": "db", "protocol": "tcp", "authorized_scope": "test",
         "native_enforcement_point": "gateway"},
    ]
    campaign = {
        "schema_version": 1, "independent_approval_verified": True,
        "native_write_authorized": False, "authorized_scope": "test",
        "observer_principal": "test-agent", "writer_principal": "operator",
        "native_policy_generation": "generation-123",
        "expires_at": 1100, "probes": probes,
    }
    def execute(p):
        return {"connected": p["expected"] == "allow",
                "application_handshake": p["expected"] == "allow"}
    def native(p):
        return {
            "enforcement_point": "gateway", "packet_identity_sha256": fingerprint(p),
            "observed_by": "test-agent", "observed_at": 1000,
            "native_trace_receipt": "trace-" + p["id"],
            "native_policy_generation": "generation-123",
            "decision": p["expected"], "counter_increased": True,
        }
    result = probe_collect(campaign, execute, native, 1000)
    assert result["status"] == "observed_not_authorized"
    assert {x["outcome"] for x in result["probes"]} == {"allow", "deny"}
    def timeout_only(p):
        row = native(p)
        if p["expected"] == "deny":
            row["decision"] = None
        return row
    with pytest.raises(CollectionFailure, match="independent_native_probe_failed"):
        probe_collect(campaign, execute, timeout_only, 1000)
