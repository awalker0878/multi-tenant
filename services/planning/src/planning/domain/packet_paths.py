"""Independent finite multipath/PBR and full packet NAT/PAT proof.

No backend-specific API call is made here; all paths and witness receipts
must originate from commissioned, signed read-only native observers.
"""
from ipaddress import ip_address
from typing import Any

from planning.domain.model import digest

MAX_PATHS = 16
MAX_HOPS = 32


class PathUnqualified(ValueError):
    pass


def insist(ok: bool, message: str) -> None:
    if not ok:
        raise PathUnqualified(message)


def packet(value: Any) -> dict[str, Any]:
    insist(isinstance(value, dict) and set(value) == {
        "source_ip", "destination_ip", "source_port", "destination_port",
        "protocol", "address_family", "scope",
    }, "native_packet_tuple_incomplete")
    try:
        src, dst = ip_address(value["source_ip"]), ip_address(value["destination_ip"])
    except (ValueError, TypeError):
        raise PathUnqualified("native_packet_address_invalid") from None
    insist(src.version == dst.version
           and value["address_family"] == ("ipv4" if src.version == 4 else "ipv6")
           and value["protocol"] in ("tcp", "udp", "icmp")
           and isinstance(value["scope"], str) and value["scope"],
           "native_packet_context_unqualified")
    for name in ("source_port", "destination_port"):
        port = value[name]
        insist((port is None and value["protocol"] == "icmp")
               or (type(port) is int and 0 <= port <= 65535),
               "native_packet_port_invalid")
    return dict(value)


def qualify(document: dict[str, Any], flow: dict[str, Any], now: int) -> dict[str, Any]:
    """Qualify *every possible* path in a provider-observed finite ECMP set."""
    paths, probes = document.get("paths"), document.get("path_probes")
    insist(document.get("all_paths_observed") is True
           and isinstance(paths, list) and 1 <= len(paths) <= MAX_PATHS
           and isinstance(probes, dict)
           and document.get("routing_generation_id")
           and document.get("observer_principal") != document.get("writer_principal"),
           "native_multipath_unqualified")
    fingerprints = []
    refs = []
    seen_path_ids = set()
    for path in paths:
        insist(isinstance(path, dict) and isinstance(path.get("id"), str)
               and path["id"] not in seen_path_ids
               and path.get("routing_generation_id") == document["routing_generation_id"]
               and path.get("complete") is True
               and isinstance(path.get("hops"), list)
               and 1 <= len(path["hops"]) <= MAX_HOPS
               and isinstance(path.get("nodes"), list)
               and len(path["nodes"]) == len(path["hops"]) + 1
               and len(path["nodes"]) == len(set(path["nodes"]))
               and path["nodes"][0] == flow["from"]
               and path["nodes"][-1] == flow["to"],
               "native_path_incomplete")
        seen_path_ids.add(path["id"])
        state = packet(path.get("ingress_packet"))
        insist(state["protocol"] == flow["protocol"]
               and state["destination_port"] == flow["port"],
               "path_application_packet_mismatch")
        used_refs = set()
        for index, hop in enumerate(path["hops"]):
            insist(isinstance(hop, dict) and hop.get("from") == path["nodes"][index]
                   and hop.get("to") == path["nodes"][index+1]
                   and isinstance(hop.get("native_ref"), str) and hop["native_ref"]
                   and hop["native_ref"] not in used_refs
                   and hop.get("ingress_packet") == state
                   and hop.get("forward_observed") is True
                   and hop.get("reverse_observed") is True
                   and hop.get("policy_route_evaluated") is True,
                   "native_hop_or_policy_route_unqualified")
            used_refs.add(hop["native_ref"])
            translated = hop.get("nat")
            if translated is None:
                out = packet(hop.get("egress_packet"))
                insist(out == state, "unqualified_packet_transformation")
            else:
                insist(isinstance(translated, dict)
                       and translated.get("type") in ("snat", "dnat", "twice_nat", "pat")
                       and isinstance(translated.get("native_ref"), str)
                       and translated.get("reverse_binding_observed") is True
                       and translated.get("before") == state,
                       "native_nat_mapping_unqualified")
                out = packet(translated.get("after"))
                insist(out == hop.get("egress_packet")
                       and out["protocol"] == state["protocol"]
                       and out["address_family"] == state["address_family"]
                       and (out["scope"] == state["scope"]
                            or translated.get("scope_crossing_qualified") is True),
                       "native_nat_translation_unqualified")
            state = out
            refs.append(hop["native_ref"])
        insist(path.get("egress_packet") == state
               and path.get("reverse_path_measured") is True,
               "native_reverse_packet_path_missing")
        witness = probes.get(path["id"])
        insist(isinstance(witness, dict)
               and witness.get("path_sha256") == digest(path)
               and witness.get("forward") == "allow"
               and witness.get("reverse") == "allow"
               and witness.get("observer") == document.get("observer_principal")
               and isinstance(witness.get("native_receipt"), str)
               and witness["native_receipt"]
               and type(witness.get("observed_at")) is int
               and 0 <= now - witness["observed_at"] <= 30
               and type(witness.get("expires_at")) is int
               and now < witness["expires_at"] <= witness["observed_at"] + 60,
               "native_path_forward_reverse_measurements_missing")
        fingerprints.append(digest(path))
    insist(document.get("path_set_sha256") == digest(sorted(fingerprints)),
           "native_path_universe_incomplete")
    return {"status": "qualified", "path_sha256": document["path_set_sha256"],
            "native_route_refs": sorted(set(refs)),
            "native_write_authorized": False}
