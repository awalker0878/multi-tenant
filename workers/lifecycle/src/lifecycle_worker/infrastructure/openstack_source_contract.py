"""Generated native configuration projection; runtime status is separate."""

from typing import Any

FIELDS = {
    "server": (
        "id",
        "tenant_id",
        "flavor",
        "image",
        "metadata",
        "addresses",
        "security_groups",
        "os-extended-volumes:volumes_attached",
        "OS-EXT-AZ:availability_zone",
        "OS-EXT-SRV-ATTR:root_device_name",
        "config_drive",
        "key_name",
    ),
    "volume": (
        "id",
        "size",
        "volume_type",
        "encrypted",
        "multiattach",
        "bootable",
        "attachments",
        "volume_image_metadata",
        "metadata",
    ),
}


def configuration(kind: str, document: dict[str, Any]) -> dict[str, Any]:
    return {key: document.get(key) for key in FIELDS[kind]}
