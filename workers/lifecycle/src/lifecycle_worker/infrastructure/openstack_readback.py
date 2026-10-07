"""P07 independent, project-scoped OpenStack infrastructure readback.

Only exact state IDs are read. Missing state, 404, changed fields and hidden project
attributes never prove safe absence or authorize a duplicate create.
"""

import json
from collections.abc import Callable
from datetime import datetime
from typing import Any, Protocol

from lifecycle_worker.application.native import (
    EXPECTED_FIELDS,
    RESOURCE_TYPES,
    NativeBinding,
    NativeHeld,
    digest,
    native_identity,
)


class ReadTransport(Protocol):
    def get(self, service: str, path: str, *, subject: bool = False) -> dict[str, Any]: ...


def state_objects(state: dict[str, Any]) -> dict[str, dict[str, Any]]:
    if not isinstance(state.get("resources"), list) or len(state["resources"]) > 128:
        raise NativeHeld("invalid_native_state_resources")
    result: dict[str, dict[str, Any]] = {}
    for resource in state["resources"]:
        if (
            not isinstance(resource, dict)
            or resource.get("mode") != "managed"
            or resource.get("type") not in RESOURCE_TYPES
            or resource.get("provider")
            != 'provider["registry.terraform.io/terraform-provider-openstack/openstack"]'
            or not isinstance(resource.get("instances"), list)
            or not 1 <= len(resource["instances"]) <= 128
        ):
            raise NativeHeld("unexpected_native_state_resource")
        for instance in resource["instances"]:
            if instance.get("deposed") or instance.get("status") == "tainted":
                raise NativeHeld("native_state_requires_repair")
            address = resource["type"] + "." + resource["name"]
            if resource.get("module"):
                address = resource["module"] + "." + address
            if "index_key" in instance:
                index = instance["index_key"]
                if type(index) not in {str, int}:
                    raise NativeHeld("invalid_native_state_index")
                address += "[" + json.dumps(index, ensure_ascii=True) + "]"
            attributes = instance.get("attributes")
            if address in result or not isinstance(attributes, dict):
                raise NativeHeld("ambiguous_native_state_resource")
            native_identity(attributes.get("id"))
            result[address] = {"kind": RESOURCE_TYPES[resource["type"]], "attributes": attributes}
    if len(result) > 128:
        raise NativeHeld("native_state_bound")
    return result


class OpenStackReadback:
    def __init__(
        self,
        transport: ReadTransport,
        resources: dict[str, Any],
        observer_user_id: str,
        writer_user_id: str,
        clock: Callable[[], int],
    ) -> None:
        self.transport, self.resources, self.clock = transport, resources, clock
        self.observer_user_id = native_identity(observer_user_id)
        self.writer_user_id = native_identity(writer_user_id)
        if observer_user_id == writer_user_id:
            raise NativeHeld("independent_native_identity_required")

    def observe(self, binding: NativeBinding, state: dict[str, Any]) -> dict[str, Any]:
        token = self.transport.get("identity", "/auth/tokens", subject=True).get("token", {})
        try:
            expiry = datetime.fromisoformat(token["expires_at"].replace("Z", "+00:00"))
            if (
                expiry.tzinfo is None
                or token.get("project", {}).get("id") != binding.project_id
                or token.get("user", {}).get("id") != self.observer_user_id
                or expiry.timestamp() <= self.clock()
            ):
                raise ValueError
        except (KeyError, ValueError, TypeError):
            raise NativeHeld("native_observer_scope_denied") from None
        objects = state_objects(state)
        if set(objects) - set(self.resources):
            raise NativeHeld("unowned_native_state_resource")
        observations: list[dict[str, Any]] = []
        for address, contract in self.resources.items():
            row = objects.get(address)
            if row is None:
                observations.append(
                    {"address": address, "outcome": "held", "reason": "state_id_unknown"}
                )
                continue
            if row["kind"] != contract["kind"]:
                raise NativeHeld("native_resource_kind_changed")
            attributes = row["attributes"]
            kind = contract["kind"]
            service, collection = {
                "server": ("compute", "servers"),
                "port": ("network", "ports"),
                "volume": ("volume", "volumes"),
            }[kind]
            try:
                document = self.transport.get(service, f"/{collection}/{attributes['id']}")
                native = document.get(kind)
                if not isinstance(native, dict) or native.get("id") != attributes["id"]:
                    raise NativeHeld("native_identity_changed")
                self.compare(binding, kind, contract["expected"], attributes, native, objects)
                observations.append(
                    {
                        "address": address,
                        "native_id": native["id"],
                        "outcome": "observed_present",
                        "observation_sha256": digest(document),
                    }
                )
            except NativeHeld as error:
                observations.append({"address": address, "outcome": "held", "reason": str(error)})
        return {
            "binding_sha256": binding.fingerprint,
            "outcome": "observed_present"
            if observations and all(r["outcome"] == "observed_present" for r in observations)
            else "held",
            "independent": True,
            "observer_user_id": self.observer_user_id,
            "observed_at": self.clock(),
            "objects": observations,
            "state_sha256": digest(state),
            "retry_authorized": False,
            "application_ready": False,
            "activation_authorized": False,
        }

    @staticmethod
    def compare(
        binding: NativeBinding,
        kind: str,
        expected: dict[str, Any],
        attributes: dict[str, Any],
        native: dict[str, Any],
        objects: dict[str, dict[str, Any]],
    ) -> None:
        if set(expected) - EXPECTED_FIELDS[kind]:
            raise NativeHeld("native_field_readback_not_implemented")
        if any(digest(attributes.get(k)) != digest(v) for k, v in expected.items()):
            raise NativeHeld("terraform_expected_fields_changed")
        project = native.get("project_id", native.get("tenant_id"))
        if kind == "volume":
            project = native.get("os-vol-tenant-attr:tenant_id", project)
            # Cinder does not expose project IDs to every reader. The bound Keystone token
            # and exact ID plus ownership metadata are still mandatory.
            if project is None:
                project = binding.project_id
        if project != binding.project_id:
            raise NativeHeld("native_project_changed")
        if "name" in expected and native.get("name") != expected["name"]:
            raise NativeHeld("native_name_changed")
        if "availability_zone" in expected:
            zone = (
                native.get("OS-EXT-AZ:availability_zone")
                if kind == "server"
                else native.get("availability_zone")
            )
            if zone != expected["availability_zone"]:
                raise NativeHeld("native_placement_changed")
        if kind in {"server", "volume"}:
            metadata = native.get("metadata", {})
            required = expected.get("metadata", {}) | {
                "product_tenant_id": binding.tenant_id,
                "product_resource_id": binding.resource_id,
            }
            if not isinstance(metadata, dict) or any(
                metadata.get(k) != v for k, v in required.items()
            ):
                raise NativeHeld("native_ownership_changed")
        if kind == "server":
            if "config_drive" in expected:
                drive = native.get("config_drive")
                if (
                    type(drive) not in {bool, str}
                    or drive not in {True, False, "True", ""}
                    or (drive in {True, "True"}) != expected["config_drive"]
                ):
                    raise NativeHeld("native_config_drive_changed")
            if (
                native.get("status") != "ACTIVE"
                or native.get("flavor", {}).get("id") != expected.get("flavor_id")
                or native.get("name") != expected.get("name")
            ):
                raise NativeHeld("native_server_not_ready")
            volumes = {
                item["uuid"]
                for item in attributes.get("block_device", [])
                if item.get("source_type") == "volume" and item.get("destination_type") == "volume"
            }
            known_volumes = {
                r["attributes"]["id"] for r in objects.values() if r["kind"] == "volume"
            }
            if not volumes or not volumes.issubset(known_volumes):
                raise NativeHeld("native_volume_state_mapping_missing")
            attached = {v.get("id") for v in native.get("os-extended-volumes:volumes_attached", [])}
            if attached != volumes:
                raise NativeHeld("native_volume_mapping_changed")
        elif kind == "port":

            def ips(value: Any) -> set[tuple[str, str]]:
                if not isinstance(value, list) or not value:
                    raise NativeHeld("native_address_missing")
                return {(str(v["subnet_id"]), str(v["ip_address"])) for v in value}

            servers = {
                r["attributes"]["id"]
                for r in objects.values()
                if r["kind"] == "server"
                and any(n.get("port") == native["id"] for n in r["attributes"].get("network", []))
            }
            if (
                native.get("description") != f"product:{binding.tenant_id}:{binding.resource_id}"
                or native.get("port_security_enabled") is not True
                or native.get("admin_state_up") is not False
                or native.get("security_groups") is None
                or set(native["security_groups"]) != set(expected.get("security_group_ids", []))
                or native.get("network_id") != expected.get("network_id")
                or len(servers) != 1
                or native.get("device_id") not in servers
                or ips(native.get("fixed_ips")) != ips(expected.get("fixed_ip"))
            ):
                raise NativeHeld("native_port_mapping_or_quarantine_changed")
        else:
            if (
                "image_id" in expected
                and native.get("volume_image_metadata", {}).get("image_id") != expected["image_id"]
            ):
                raise NativeHeld("native_image_changed")
            servers = {
                r["attributes"]["id"]
                for r in objects.values()
                if r["kind"] == "server"
                and any(
                    d.get("uuid") == native["id"] for d in r["attributes"].get("block_device", [])
                )
            }
            if (
                not servers
                or {a.get("server_id") for a in native.get("attachments", [])} != servers
            ):
                raise NativeHeld("native_volume_attachment_changed")
            if (
                native.get("status") != "in-use"
                or type(native.get("size")) is not int
                or native.get("size") != expected.get("size")
                or native.get("volume_type") != expected.get("volume_type")
                or native.get("name") != expected.get("name")
            ):
                raise NativeHeld("native_volume_not_ready")
