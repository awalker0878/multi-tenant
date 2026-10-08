"""Current P09 owner protocols over fixed, separately authenticated TLS origins."""

import json
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from lifecycle.domain.admission import digest
from lifecycle.domain.execution import Rejected, decode, identity
from lifecycle.domain.expansion import operation
from lifecycle.domain.native_workflow import checksum, exact, integer
from lifecycle.infrastructure.campaign_observers import protected
from lifecycle.infrastructure.native_effects import NativeEffectConnection, credential
from lifecycle.infrastructure.native_owners import endpoint


class ExpansionOwners:
    def __init__(self, path: Path, clock: Callable[[], int]) -> None:
        self.path, self.clock = path, clock

    def load(self) -> dict[str, Any]:
        value = decode(protected(str(self.path), 1048576))
        exact(value, {"schema_version", "expires_at", "owners", "observer_id", "writer_id"})
        if (
            type(value["schema_version"]) is not int
            or value["schema_version"] != 1
            or integer(value["expires_at"]) <= self.clock()
        ):
            raise Rejected("expansion_owner_configuration_expired", 423)
        identity(value["observer_id"]), identity(value["writer_id"])
        if value["observer_id"] == value["writer_id"]:
            raise Rejected("expansion_observer_must_be_independent", 423)
        exact(value["owners"], {"plans", "authority", "budgets", "observations", "adoption"})
        tokens = [credential(endpoint(e).credential_file) for e in value["owners"].values()]
        if len(set(tokens)) != len(tokens):
            raise Rejected("expansion_owner_credentials_must_be_distinct", 423)
        return value

    def request(self, owner: str, body: dict[str, Any]) -> dict[str, Any]:
        paths = {
            "plans": "/v1/expansion/plan",
            "authority": "/v1/expansion/authority",
            "budgets": "/v1/expansion/budgets",
            "observations": "/v1/expansion/observation",
            "adoption": "/v1/expansion/adoption-observation",
        }
        initial = self.load()
        target = endpoint(initial["owners"][owner])
        connection = NativeEffectConnection(target)
        try:
            connection.request(
                "POST",
                paths[owner],
                body=json.dumps(body, allow_nan=False).encode(),
                headers={
                    "Authorization": "Bearer " + credential(target.credential_file),
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                    "Accept-Encoding": "identity",
                },
            )
            response = connection.getresponse()
            if (
                response.status != 200
                or response.getheader("Content-Type", "").split(";")[0] != "application/json"
                or response.getheader("Content-Encoding", "identity") != "identity"
            ):
                raise Rejected("expansion_owner_unavailable", 423)
            raw = bytearray()
            deadline = time.monotonic() + 5
            while True:
                if time.monotonic() >= deadline:
                    raise Rejected("expansion_owner_response_deadline", 423)
                part = response.read1(min(65536, 1048577 - len(raw)))
                raw.extend(part)
                if len(raw) > 1048576:
                    raise Rejected("expansion_owner_response_bound", 423)
                if not part:
                    break
            if digest(initial) != digest(self.load()):
                raise Rejected("expansion_owner_response_held", 423)
            return decode(bytes(raw))
        except Rejected:
            raise
        except Exception:
            raise Rejected("expansion_owner_unavailable", 423) from None
        finally:
            connection.close()

    def plan(self, tenant: str, ref: dict[str, Any]) -> dict[str, Any]:
        result = self.request("plans", {"tenant_id": tenant, "reference": ref})
        exact(result, {"reference", "specification"})
        spec = operation(result["specification"])
        if (
            result["reference"] != ref
            or spec["tenant_id"] != tenant
            or digest(spec) != ref["sha256"]
        ):
            raise Rejected("enterprise_plan_binding_changed", 423)
        return spec

    def require_current(self, specification: dict[str, Any], boundary: str) -> None:
        value = self.request(
            "authority",
            {
                "specification_sha256": digest(specification),
                "tenant_id": specification["tenant_id"],
                "boundary": boundary,
            },
        )
        exact(
            value,
            {
                "specification_sha256",
                "tenant_id",
                "boundary",
                "prerequisites",
                "current",
                "observed_at",
                "expires_at",
            },
        )
        if (
            value["current"] is not True
            or value["tenant_id"] != specification["tenant_id"]
            or value["boundary"] != boundary
            or value["specification_sha256"] != digest(specification)
            or value["prerequisites"] != specification["prerequisites"]
            or not 0 <= self.clock() - integer(value["observed_at"]) <= 5
            or integer(value["expires_at"]) <= self.clock()
        ):
            raise Rejected("enterprise_current_authority_held", 423)

    def budgets(self, pools: list[str]) -> dict[str, Any]:
        return self.request("budgets", {"pools": pools})

    def observe(self, specification: dict[str, Any], lease: str) -> dict[str, Any]:
        value = self.request(
            "observations",
            {
                "specification_sha256": digest(specification),
                "operation_id": specification["id"],
                "tenant_id": specification["tenant_id"],
                "lease": lease,
            },
        )
        config = self.load()
        if (
            value.get("observer_id") != config["observer_id"]
            or value.get("executor_id") != config["writer_id"]
        ):
            raise Rejected("expansion_observer_identity_changed", 423)
        return value


class AdoptionObservations:
    def __init__(self, owners: ExpansionOwners) -> None:
        self.owners = owners

    def observe(
        self, tenant: str, native_scope: dict[str, Any], selected: list[str]
    ) -> dict[str, Any]:
        for name in selected:
            if not isinstance(name, str):
                raise Rejected("invalid_adoption_field", 422)
        checksum(native_scope["tuple_sha256"])
        value = self.owners.request(
            "adoption", {"tenant_id": tenant, "scope": native_scope, "fields": selected}
        )
        config = self.owners.load()
        if (
            value.get("observer_id") != config["observer_id"]
            or value.get("writer_id") != config["writer_id"]
        ):
            raise Rejected("expansion_observer_identity_changed", 423)
        return value
