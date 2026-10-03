# OpenStack project quota owner

[Automation home](README.md) · [Capacity reservations](capacity-reservations.md) · [Reference decisions](reference-realization.md)

`provisioner/execution/openstack_quota.py` applies exact accepted limits to an existing tenant
project through Nova, Cinder or Neutron. It verifies the administrative token,
native target project, selected catalog endpoint, current limits and usage
before one native PUT. Durable intent prevents an interrupted controller from
repeating an uncertain write. Recovery reads the original requested limits.

This owner changes project quota fields. It does not create projects, grant
roles, change placement, reserve physical capacity or prove delegated isolation.
Capacity admission remains a separate owner. Commission the actual installed
quota driver and enforcement policy before using this profile; a successful
legacy quota API response is not evidence that every installed quota driver
enforces those limits. Unified-limit or otherwise different enforcement requires
its own accepted implementation.

## Supported native interfaces

| Service | Request profile | Owned field choices |
| --- | --- | --- |
| Compute | Nova `compute 2.79`, project quota detail/read and update | `cores`, `instances`, `ram`, `server_groups`, `server_group_members` |
| Volume | Cinder `volume 3.60`, quota read with `usage=True` and update | `volumes`, `snapshots`, `gigabytes`, `backups`, `backup_gigabytes`, `groups` |
| Network | Neutron v2.0 `quota_details` and project quota update | `network`, `subnet`, `port`, `router`, `floatingip`, `security_group`, `security_group_rule`, `rbac_policy`, `subnetpool` |

One request selects a nonempty exact subset. The first generation establishes
that field set; later generations preserve it and name the previous accepted
limits. Unselected fields are neither submitted nor adopted into this owner's
quota history. Per-user, per-volume-type and quota-class changes are unsupported.
Native units are retained: Nova RAM is MiB; Cinder sizes use its documented GB
quota units. Do not equate them to the capacity owner's decimal accounting
without an accepted conversion.

All target limits are finite and nonnegative. An explicitly observed initial
unlimited value of -1 can be replaced with a finite accepted limit. The owner
never sends force, deletes quota records, resets defaults or silently creates
an unlimited allocation. Used plus reserved resources must fit the target limit
both before and after the write.

## Exact request and authority

The private strict JSON `hosting-openstack-quota/1` request contains:

| Fields | Binding |
| --- | --- |
| `format`, `enabled` | `hosting-openstack-quota/1` and explicit Boolean execution selection |
| `source_commit`, `operation_id`, `generation` | Exact clean owner source, stable operation identity, consecutive generation starting at 1 |
| `scope` | Exactly environment, site, platform and tenant keys; platform is `openstack` |
| `service` | `compute`, `volume` or `network` |
| `identity_endpoint`, `endpoint` | Accepted exact HTTPS identity-v3 and quota service catalog URLs, without trailing slash |
| `project` | Exact `id`, `domain_id`, `parent_id`, `name`; parent may be null |
| `caller` | Exact `user_id`, `user_domain_id`, `project_id`, `project_domain_id`, `role_ids`, `region`, `interface` |
| `before`, `after` | Maps of the same supported quota fields to exact native limits |
| `entitlement_ref`, `enforcement_ref` | Accepted tenant limits/capacity relationship and installed quota-driver enforcement evidence |

The administrative caller's project is distinct from the target tenant.
`role_ids` is a sorted unique list of accepted native role IDs; role names
are not inferred as authority. The selected interface is internal or admin.
Domain IDs support the native `default` domain as well as exact hexadecimal
or UUID identities. Project/user/role IDs must be exact hexadecimal or UUID IDs.

Compute endpoints end with `/v2.1` or `/v2.1/<caller-project>`;
Cinder endpoints end with `/v3/<caller-project>`; Neutron ends with
`/v2.0`. The selected endpoint, interface, region and service type must
appear exactly once in the current token catalog. The issuer verifies the token
through Keystone's token validation API using both required token headers.
The enabled target's project ID, name, domain and parent must match, and it must
not be a domain object.

The private `hosting-openstack-quota-authority/1` record contains
`format`, `request_sha256`, `action`, `token_sha256`, `ca_sha256`, `valid_from`, `valid_until`, `change_ref`, `writer_exclusion_ref`.
`action` is apply or observe; authority is current and at most one hour.
The request digest uses `readback_core.digest`; credential and CA digests
bind exact input bytes. The trusted CA is mandatory. Tokens are injected through
a private file and never retained in receipts or printed diagnostics.

```sh
python -m provisioner.execution.openstack_quota --source-root /opt/hosting-source --request /private/quota-request.json
python -m provisioner.execution.openstack_quota --source-root /opt/hosting-source --request /private/quota-request.json \
  --authority /private/quota-authority.json --token /private/quota-token \
  --ca /private/service-ca.pem --ledger /private/quota-ledger --execute
```

## Recovery and ownership

All controllers use the same protected ledger. The lock and history are keyed
by service endpoint and target project, independent of operation name and caller
project suffix. Changing administrative credentials or their project path does
not create a new history for the same native quota scope. Endpoint aliases or a
second ledger cannot be discovered automatically; the accepted service owner
must maintain one canonical endpoint and effective quota writer exclusion.

Preflight reads current usage twice. Changed limits or usage, expired identity,
wrong roles, redirects, wrong microversions, missing fields and ambiguous
responses hold before a new write. A permanent `QUOTA_CHANGE_STARTED`
event precedes the PUT. The owner checks the response and fresh native state,
rechecks identity and project, and only then records completion and a private
observed quota receipt. No-op requests still record ownership and observation
without a PUT.

If the PUT or later verification is interrupted, preserve the existing intent
and publish a fresh observe authority for the identical original request.
Recovery performs GETs only and requires the desired limits to be present.
An absent change remains unknown; it is never retried automatically. A renamed
operation or higher generation cannot bypass that uncertainty. After completion,
the next generation must name the previous limits. Superseded requests cannot
be replayed as current observations.

These native APIs do not provide this owner with compare-and-swap quota writes.
Stable preflight reads and a local file lock are not a native fence. The accepted
maintenance procedure must exclude quota and allocation writers for the affected
scope. The receipt explicitly leaves native fencing, delegated RBAC qualification,
physical capacity reservation and production activation false.

Real TLS fixtures exercise all three API profiles, exact headers/payloads,
quota/usage drift, identity mismatch, lost responses, competing controllers,
held generations and read-only recovery. They do not emulate installed
OpenStack enforcement or close the project's native entitlement qualification.

Interface references: [Nova quotas](https://docs.openstack.org/api-ref/compute/#quota-sets-os-quota-sets),
[Cinder quotas](https://docs.openstack.org/api-ref/block-storage/v3/#quota-sets-extension-os-quota-sets),
[Neutron quota details](https://docs.openstack.org/api-ref/network/v2/index.html#quotas-details-extension-quota-details)
and [Keystone token validation](https://docs.openstack.org/api-ref/identity/v3/#validate-and-show-information-for-token).
