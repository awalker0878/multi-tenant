"""Current owner profiles are the only source of migration identities and datasets."""

from copy import deepcopy
from typing import Any
from unittest.mock import Mock
from uuid import uuid4

import pytest
from test_planning_http import exchange

from planning.domain.migration import bind_migration
from planning.domain.model import Rejected, digest
from planning.interfaces.migration import MigrationPreparationApp


def inputs() -> dict[str, Any]:
    dataset = str(uuid4())
    return {
        "current": True,
        "native_write_authorized": False,
        "revision": 1,
        "digest": digest("review"),
        "method": "VM_COLD_EXPORT",
        "target_disk_formats": ["raw"],
        "source": {"observed_at": 990, "expires_at": 1100},
        "target": {"observed_at": 990, "expires_at": 1100},
        "disks": [{"key": 2000, "native_sha256": digest("disk"), "capacity_bytes": 1024}],
        "datasets": [{"id": dataset, "disk_keys": [2000]}],
        "owner_inputs": {"consistency": "owner"},
        "objectives": {"outage": 100},
    }


def mapping() -> list[dict[str, Any]]:
    return [{"source_disk_sha256": digest("disk"), "target_key": str(uuid4()), "format": "raw"}]


def test_native_capacities_and_datasets_are_derived_from_current_owner() -> None:
    i = inputs()
    bound = bind_migration(i, mapping(), 1000)
    assert bound["datasets"] == [i["datasets"][0]["id"]]
    assert bound["disks"][0]["capacity_bytes"] == 1024
    assert bound["review"] == {"revision": 1, "digest": i["digest"]}
    assert bound["owner_inputs_sha256"] == digest(i["owner_inputs"])


@pytest.mark.parametrize(
    "fault", ["stale", "unconfirmed", "missing", "foreign", "capacity", "format", "duplicate"]
)
def test_missing_stale_and_client_invented_native_values_fail(fault: str) -> None:
    i, rows = inputs(), mapping()
    if fault == "stale":
        i["source"]["expires_at"] = 1000
    elif fault == "unconfirmed":
        i["current"] = False
    elif fault == "missing":
        rows = []
    elif fault == "foreign":
        rows[0]["source_disk_sha256"] = digest("other")
    elif fault == "capacity":
        rows[0]["capacity_bytes"] = 1
    elif fault == "format":
        rows[0]["format"] = "qcow2"
    else:
        rows.append(deepcopy(rows[0]))
    with pytest.raises(Rejected):
        bind_migration(i, rows, 1000)


def test_migration_preparation_requires_scoped_actor_before_owner_read() -> None:
    import json

    from planning_fixture import SITE

    authority, prepare = Mock(), Mock(return_value={"review": "bound"})
    app: Any = MigrationPreparationApp(authority, prepare)
    body = {
        "site_id": SITE,
        "review": {"revision": 1, "digest": digest("review")},
        "disks": mapping(),
    }
    headers = [
        (b"authorization", b"Bearer " + b"a" * 64),
        (b"content-type", b"application/json"),
        (b"x-actor-delegation", b"b" * 64),
    ]
    status, result = exchange(app, "/migration-preparations", json.dumps(body).encode(), headers)
    assert status == 200 and result["native_write_authorized"] is False
    assert authority.actor.call_args.args[3] == "plan.create"
    prepare.reset_mock()
    authority.actor.side_effect = Rejected("denied", 403)
    assert exchange(app, "/migration-preparations", json.dumps(body).encode(), headers)[0] == 403
    prepare.assert_not_called()


def test_ahv_owner_mapping_is_bound_into_preparation() -> None:
    i = inputs()
    i["destination"] = {"platform": "ahv", "cluster_id": str(uuid4()), "nics": []}
    bound = bind_migration(i, mapping(), 1000)
    assert bound["destination_sha256"] == digest(i["destination"])
