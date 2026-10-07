"""Independent native object readback from durable API receipts, never process state."""

from collections.abc import Callable
from datetime import datetime
from typing import Any, Protocol

from lifecycle_worker.application.native import NativeBinding, NativeHeld, digest, native_identity


class ReadTransport(Protocol):
    def get(self, service: str, path: str, *, subject: bool = False) -> dict[str, Any]: ...


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
        if self.observer_user_id == self.writer_user_id:
            raise NativeHeld("independent_native_identity_required")

    def observe(self, binding: NativeBinding, objects: dict[str, Any]) -> dict[str, Any]:
        token = self.transport.get("identity", "/auth/tokens", subject=True).get("token", {})
        try:
            expiry = datetime.fromisoformat(token["expires_at"].replace("Z", "+00:00"))
            if (
                expiry.tzinfo is None
                or expiry.timestamp() <= self.clock()
                or token.get("project", {}).get("id") != binding.project_id
                or token.get("user", {}).get("id") != self.observer_user_id
            ):
                raise ValueError
        except (KeyError, ValueError, TypeError):
            raise NativeHeld("native_observer_scope_denied") from None
        if not isinstance(objects, dict) or set(objects) - set(self.resources):
            raise NativeHeld("unowned_native_receipt")
        observations = []
        for key, resource in self.resources.items():
            kind, expected = resource["kind"], resource["spec"]
            try:
                row = objects.get(key)
                if not isinstance(row, dict) or row.get("kind") != kind:
                    raise NativeHeld("native_object_identity_unknown")
                object_id = native_identity(row.get("id"))
                service, path = {
                    "port": ("network", "/ports/"),
                    "volume": ("volume", "/volumes/"),
                    "server": ("compute", "/servers/"),
                }[kind]
                document = self.transport.get(service, path + object_id)
                native = document.get(kind)
                if not isinstance(native, dict) or native.get("id") != object_id:
                    raise NativeHeld("native_object_identity_changed")
                self.compare(binding, key, kind, expected, native, objects)
                if kind == "server":
                    interfaces = self.transport.get(
                        "compute", "/servers/" + object_id + "/os-interface"
                    )
                    actual = {entry["port_id"] for entry in interfaces["interfaceAttachments"]}
                    if actual != {objects[port]["id"] for port in expected["ports"]}:
                        raise NativeHeld("native_server_interfaces_changed")
                observations.append(
                    {
                        "resource_key": key,
                        "native_id": object_id,
                        "outcome": "observed_present",
                        "observation_sha256": digest(document),
                    }
                )
            except NativeHeld as error:
                observations.append({"resource_key": key, "outcome": "held", "reason": str(error)})
        return {
            "binding_sha256": binding.fingerprint,
            "independent": True,
            "observer_user_id": self.observer_user_id,
            "observed_at": self.clock(),
            "outcome": "observed_present"
            if observations and all(row["outcome"] == "observed_present" for row in observations)
            else "held",
            "objects": observations,
            "receipt_set_sha256": digest(objects),
            "retry_authorized": False,
            "application_ready": False,
            "activation_authorized": False,
        }

    def compare(
        self,
        binding: NativeBinding,
        key: str,
        kind: str,
        expected: dict[str, Any],
        native: dict[str, Any],
        objects: dict[str, Any],
    ) -> None:
        project = native.get("project_id", native.get("tenant_id"))
        if kind == "volume":
            project = native.get("os-vol-tenant-attr:tenant_id", project)
            if project is None:
                project = binding.project_id
        if project != binding.project_id or native.get("name") != expected["name"]:
            raise NativeHeld("native_project_or_name_changed")
        if kind in {"server", "volume"}:
            required = {
                "product_tenant_id": binding.tenant_id,
                "product_resource_id": binding.resource_id,
                "product_operation_id": binding.operation_id,
                "product_object_key": key,
            }
            if any(native.get("metadata", {}).get(k) != value for k, value in required.items()):
                raise NativeHeld("native_ownership_changed")
            zone = (
                native.get("OS-EXT-AZ:availability_zone")
                if kind == "server"
                else native.get("availability_zone")
            )
            if zone != expected["availability_zone"]:
                raise NativeHeld("native_placement_changed")
        if kind == "server":
            if (
                native.get("status") != "ACTIVE"
                or native.get("flavor", {}).get("id") != expected["flavorRef"]
                or not (native.get("config_drive") is True or native.get("config_drive") == "True")
            ):
                raise NativeHeld("native_server_not_ready")
            volumes = {objects[disk["key"]]["id"] for disk in expected["volumes"]}
            attached = {
                disk["id"] for disk in native.get("os-extended-volumes:volumes_attached", [])
            }
            if volumes != attached:
                raise NativeHeld("native_volume_mapping_changed")
        elif kind == "port":

            def ips(value: Any) -> set[tuple[str, str]]:
                if not isinstance(value, list) or not value:
                    raise NativeHeld("native_address_missing")
                return {(entry["subnet_id"], entry["ip_address"]) for entry in value}

            servers = {
                objects[server_key]["id"]
                for server_key, server in self.resources.items()
                if server["kind"] == "server"
                and key in server["spec"]["ports"]
                and server_key in objects
            }
            if (
                native.get("description")
                != f"product:{binding.tenant_id}:{binding.resource_id}:{key}"
                or native.get("admin_state_up") is not False
                or native.get("port_security_enabled") is not True
                or native.get("network_id") != expected["network_id"]
                or native.get("security_groups") is None
                or set(native["security_groups"]) != set(expected["security_groups"])
                or ips(native.get("fixed_ips")) != ips(expected["fixed_ips"])
                or len(servers) != 1
                or native.get("device_id") not in servers
            ):
                raise NativeHeld("native_port_mapping_or_quarantine_changed")
        else:
            servers = {
                objects[server_key]["id"]
                for server_key, server in self.resources.items()
                if server["kind"] == "server"
                and any(disk["key"] == key for disk in server["spec"]["volumes"])
                and server_key in objects
            }
            if (
                not servers
                or {entry["server_id"] for entry in native.get("attachments", [])} != servers
                or native.get("status") != "in-use"
                or type(native.get("size")) is not int
                or native["size"] != expected["size"]
                or native.get("volume_type") != expected["volume_type"]
            ):
                raise NativeHeld("native_volume_mapping_or_state_changed")
            if (
                expected["imageRef"] is not None
                and native.get("volume_image_metadata", {}).get("image_id") != expected["imageRef"]
            ):
                raise NativeHeld("native_boot_image_changed")
