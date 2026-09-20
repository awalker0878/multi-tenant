# Collecting target-bound qualification evidence

`tools/qualify_target.py` runs the existing exact-ID native observers before and
after a bounded guest traffic campaign. It uses real HTTPS and certificate SSH.
It neither changes native configuration nor marks a platform/site qualified.
Use its evidence in the [native reference campaign](../native-reference/campaign.md)
and the independent acceptance process. It cannot replace HA, capacity,
delegated-administrator, same-subnet bypass, storage or whole-application recovery
tests that the campaign requires.

## Private inputs

Use owner-only files in an operator directory outside this checkout. The plan
format is `hosting-target-campaign/1`, with these exact fields:

| Field | Value |
| --- | --- |
| `scope` | `environment_key`, `site_key`, `platform`, `tenant_key`, `wsd_key` |
| `source_commit` | Full commit of the clean checkout that will run the campaign |
| `origin` | One canonical HTTPS origin for Neutron, NSX Local Manager or Prism |
| `assets` | The seven content-bound assets below |
| `cases` | 1–32 exact IPv4 HTTPS health/denial cases |

Each asset is an object with absolute `path` and SHA-256 of its exact file bytes
in `sha256`. Do not commit actual values, credentials or evidence.

| Asset | Content |
| --- | --- |
| `inventory` | Private inventory produced by [guest_inventory.py](native-guests.md); scope and native workload IDs are rebuilt and checked |
| `native_manifest` | Current exact resource IDs and expectations for the selected [native observer](../../NATIVE_READBACK.md) |
| `native_credentials` | Neutron: JSON `token`; NSX/Prism: JSON `username`, `password`; scoped read-only credentials |
| `native_ca` | PEM CA bundle for the native API |
| `ssh_key` | Unencrypted short-lived Ed25519 private operator key in protected custody |
| `ssh_certificate` | Matching user certificate accepted by the guest CA/principal policy |
| `probe_ca` | PEM CA bundle for the approved health endpoints |

The runner reconstructs SSH settings from the bound guest records, uses pinned
host keys, and requires certificate authentication. It ignores inventory command
overrides and ambient SSH configuration, proxies, agents and user key discovery.
The approved private key is copied into the private run directory for the child
client and removed on normal completion/failure. After a forced controller stop,
protect and reconcile that directory, including any remaining key copy.

Each case has exactly these fields (the digest is illustrative):

```json
{
  "id": "same-service-health",
  "guest": "guest-a",
  "destination": "192.0.2.130",
  "port": 443,
  "server_name": "service.example.test",
  "path": "/health",
  "body_sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  "expect": "allow",
  "healthy_control": null
}
```

An expected denial uses `expect: deny` and names an allow case in
`healthy_control`. That control must use a different guest but the same
destination, port, certificate name, path and body digest. The runner verifies
the control immediately before and after the denial. Failed controls or routing,
SSH, identity and TLS errors are inconclusive, not passing isolation evidence.
A successful TCP connection fails an expected denial, even if TLS later fails.
Refusal/timeout with both healthy controls is bounded path-denial evidence; it
does not identify the enforcing device. Correlate native counters/logs independently.

The fixed remote script checks `/etc/machine-id`, binds to the guest's accepted
SSH IPv4 address, and performs one connection. An allow must verify TLS identity,
HTTP 200 and the exact body digest (at most 1 MiB). No redirects, query parameters,
arbitrary remote commands, endpoint discovery or address ranges are supported.
The chosen health path must be a read-only operation owned by the service. Guests
need Python 3 and an accepted address usable for both SSH and the tested path;
multi-interface source selection needs a separately adopted profile.

## Authority and execution

Supply a `hosting-target-campaign-authority/1` object with `plan_sha256` (exact
plan bytes), `source_commit`, `ssh_sha256` (actual executable bytes),
`valid_from`, `valid_until`, `change_ref`, `target_binding_ref` and `isolation_ref`.
The window must be current and at most one hour. References identify separately
issued records; JSON is not authentication of the issuing authority. The target
binding must independently establish that native manifest resources and guest
IDs belong to the exact site/tenant/WSD. Do not infer ownership from a label.

```sh
python tools/qualify_target.py /private/operator/campaign.json
python tools/qualify_target.py /private/operator/campaign.json --execute \
  --authority /private/operator/campaign-authority.json \
  --ssh /usr/bin/ssh --output /private/operator/new-campaign
```

Without `--execute`, only the plan schema is checked and no target is contacted.
Execution validates source, assets and authority before contact. Native reads
are bounded to 120 seconds per phase; each SSH command to 20 seconds and its
remote probe to 10 seconds. The next phase is refused unless enough authority
remains for its entire timeout. Access expiry is checked before every guest call.

The private journal starts as `HOLD_INCOMPLETE`. Missing/failed native readback,
interruption or incomplete observations cannot produce acceptance. Failed traffic
stops the campaign and returns a hold. Complete matching observations return
`COLLECTED_REQUIRES_INDEPENDENT_ACCEPTANCE`, retaining the scope, source, exact
input digest, before/after readback hashes and per-probe timestamps. No accepted
qualification index is updated and no connectivity is opened by this tool.

Maintain the separate [edge lease/withdrawal](edge-activation.md) during the
campaign; on failed readiness, execute the already-authorized withdrawal.
This read-only collector cannot issue its own mutation authority or silently
renew an expiring policy. For recovery campaigns, pair these health checks with
the [restic file restore](restic-recovery.md) and application-owner acceptance.
Neither file hashes nor a health endpoint alone establish database consistency.
