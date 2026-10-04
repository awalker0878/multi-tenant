"""Explicit retained output contracts; no inferred platform compatibility."""
from dataclasses import dataclass


@dataclass(frozen=True)
class RetainedWorkloadOutput:
    scalar_bindings: tuple[tuple[str, str], ...]
    array_bindings: tuple[tuple[str, str], ...]


# Only this recorded output contract has an implemented B48 projection. Native
# identity extraction is declared with the contract rather than provider-name
# decisions inside the generic inventory/importer.
RETAINED_OUTPUT_CONTRACTS = {
    ('hosting-terraform-bundle/1', 'openstack', 'workloads'): RetainedWorkloadOutput(
        scalar_bindings=(('server_id', 'vm'), ('port_id', 'nic'), ('boot_volume_id', 'volume')),
        array_bindings=(('data_volume_ids', 'volume'),)),
}
