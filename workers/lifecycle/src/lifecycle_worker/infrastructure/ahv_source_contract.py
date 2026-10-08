"""Generated native configuration projection; runtime status is separate."""

from typing import Any

FIELDS = {
    "vm": (
        "extId",
        "name",
        "createTime",
        "generationUuid",
        "biosUuid",
        "project",
        "projectExtId",
        "cluster",
        "categories",
        "numSockets",
        "numCoresPerSocket",
        "numThreadsPerCore",
        "memorySizeBytes",
        "bootConfig",
        "vtpmConfig",
        "disks",
        "nics",
        "cdRoms",
        "gpus",
        "pcieDevices",
        "storageConfig",
    ),
}


def configuration(kind: str, document: dict[str, Any]) -> dict[str, Any]:
    return {key: document.get(key) for key in FIELDS[kind]}
