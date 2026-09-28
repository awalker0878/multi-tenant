# Supported service-profile matrix

## Capability requirements and limitations

Selected compute, storage, recovery and service profiles now declare their own
mandatory workload capabilities, in addition to the network/security requirements.
For example, boot/data storage, VM creation, DNS registration, identity join, time
synchronization, log forwarding and backup/restore cannot be satisfied by a
network-only qualification. The [platform registry](../engineering/platform-capability-registry.md)
uses one complete, digest-bound vocabulary for all three platform families.

Profile resolution retains the limitations of **every** selected profile, including
compute, storage, assurance, placement, recovery and each service. The loader rejects
malformed or duplicate capability lists, unknown IDs, ambiguous JSON properties
and invalid profile metadata rather than coercing them. Unsupported/deferred
profiles remain refused. A profile being resolvable means its policy can be
expanded; it is not proof of native execution, entitlement or qualification.

This revision changes the reviewed security/compute/storage catalogue and
profile versions. Existing plans need reassessment and new approval; do not reuse
an approval made against the previous catalogue digest. The regenerated examples
remain synthetic, disabled and unauthorized.

Every profile below is reviewed in `profiles/<family>/catalog.json`. Status
`IMPLEMENTED_INTERNAL_IPV4_OZ_RZ` means a request in this repository may select it;
`DEFERRED_NOT_IMPLEMENTED` means selection is refused with `UNSUPPORTED_PROFILE`.

Each catalog states its own reviewed revision and every profile states its own
reviewed revision. Both are repeated here so that a change to either is visible in
review, and `tests/provisioning/documentation/test_documentation.py` refuses a
matrix that drifts from the catalogs.

The catalogs are also the machine-readable owner of the portable defaults: the
default profile of a family, the portable service list and its default profiles,
and the request-shape defaults a caller may omit. `docs/provisioning/profile-model.md`
lists which family owns which default.

There is exactly one implemented realization: **internal IPv4, operations zone plus
restricted zone**. Everything outside that shape is declared and deferred so the
refusal is explicit rather than accidental.

## Environment

Reviewed as catalog revision `4`.

| Profile | Rank | Status | Requires | Version |
| --- | --- | --- | --- | --- |
| `development` | 1 | implemented | assurance ≥ 1, availability ≥ 1, security ≥ 1, recovery off | 1 |
| `test` | 2 | implemented | assurance ≥ 1, availability ≥ 1, security ≥ 1, recovery off | 1 |
| `qualification` | 3 | implemented | assurance ≥ 1, availability ≥ 1, security ≥ 1, recovery off | 1 |
| `production` | 4 | implemented | assurance ≥ 1, availability ≥ 2 (`high`), security ≥ 2, recovery on | 1 |
| `recovery` | 5 | implemented | assurance ≥ 2 (`elevated`), availability ≥ 2, security ≥ 2, recovery on | 1 |

## Security

Reviewed as catalog revision `15`.

| Profile | Rank | Status | Service class | Version |
| --- | --- | --- | --- | --- |
| `internal-baseline` | 1 | implemented | `standard` | 2 |
| `protected-b-medium` | 2 | implemented | `protected-b`, distributed firewall | 2 |
| `protected-b-high` | 3 | implemented | `protected-b`, dedicated edge context, native load balancer | 2 |

All three declare `public_ingress: false` and `internet_egress: false`.
They require independent routing context and enforced deny-default gateway policy;
profiles selecting distributed firewalling additionally require enforced policy
across every selected workload NIC. Monitor mode or a gateway-only firewall does
not fulfill that obligation.

## Assurance

Reviewed as catalog revision `1`.

| Profile | Rank | Status | Requires | Version |
| --- | --- | --- | --- | --- |
| `standard` | 1 | implemented | `audit_logging`, recovery not required | 1 |
| `elevated` | 2 | implemented | `audit_logging`, `dedicated_edge_context`, recovery required | 1 |
| `regulatory` | 3 | **deferred** | no reviewed control mapping or native evidence model | 1 |

## Availability

Reviewed as catalog revision `2`.

| Profile | Rank | Status | Zones | Version |
| --- | --- | --- | --- | --- |
| `single-zone` | 1 | implemented | `OZ` | 1 |
| `high` | 2 | implemented | `OZ`, `RZ` | 1 |
| `maximum` | 3 | **deferred** | `OZ`, `RZ`, `PAZ` — only OZ/RZ compositions exist | 1 |

## Recovery

Reviewed as catalog revision `13`.

| Profile | Rank | Status | Requires | Version |
| --- | --- | --- | --- | --- |
| `standard` | 1 | implemented | `RZ`, `backup` service | 2 |
| `enhanced` | 2 | **deferred** | independent recovery site — no such inventory exists | 2 |

## Compute

Reviewed as catalog revision `16`.

| Profile | Rank | Status | Guest | Version |
| --- | --- | --- | --- | --- |
| `small` | 1 | implemented | 2 vCPU / 4 GiB / 40 GiB boot | 3 |
| `medium` | 2 | implemented | 4 vCPU / 8 GiB / 60 GiB boot | 3 |
| `large` | 3 | implemented | 8 vCPU / 16 GiB / 80 GiB boot | 3 |
| `gpu` | 4 | **deferred** | no reviewed accelerator capacity or scheduling model | 3 |

All compute profiles now explicitly require x86_64; GPU remains deferred.

## Storage

Reviewed as catalog revision `17`.

| Profile | Rank | Status | Requires | Version |
| --- | --- | --- | --- | --- |
| `standard` | 1 | implemented | boot disk only | 2 |
| `high-capacity` | 2 | implemented | boot disk plus a 100 GiB protected data volume | 2 |
| `encrypted-high-capacity` | 3 | **deferred** | key custody and encryption qualification are not implemented | 3 |

## Network

Reviewed as catalog revision `5`.

| Profile | Rank | Status | Requires | Version |
| --- | --- | --- | --- | --- |
| `internal-ipv4` | 1 | implemented | IPv4, `/27`, offset gateway host 1 | 1 |
| `dual-stack` | 2 | **deferred** | routed IPv6 — the lab is an experiment, not a placement authority | 1 |
| `ipv6-only` | 3 | **deferred** | no qualified IPv6-only native path | 1 |

## Placement (region)

Reviewed as catalog revision `6`.

| Profile | Rank | Status | Requires | Version |
| --- | --- | --- | --- | --- |
| `east` | 1 | implemented | reviewed inventory in region `east` | 1 |
| `west` | 2 | implemented | reviewed inventory in region `west` | 1 |
| `public` | 3 | **deferred** | no public or partner exposure path is implemented | 1 |

A region profile is a filter over reviewed inventory, not a capacity promise.

## Service

Reviewed as catalog revision `14`.

| Profile | Rank | Status | Required binding class | Version |
| --- | --- | --- | --- | --- |
| `dns/default` | 1 | implemented | `dns-internal` | 2 |
| `dns/external-view` | 2 | **deferred** | `dns-external` — public name publication is out of scope | 2 |
| `ntp/default` | 1 | implemented | `ntp-internal` | 2 |
| `identity/enterprise` | 1 | implemented | `identity-directory` | 2 |
| `identity/standalone` | 2 | **deferred** | `identity-standalone` — contradicts the reviewed identity boundary | 2 |
| `logging/standard` | 1 | implemented | `logging-standard` | 2 |
| `logging/protected-b` | 2 | implemented | `logging-protected` | 2 |
| `backup/standard` | 1 | implemented | `backup-isolated` | 2 |
| `backup/enhanced` | 2 | **deferred** | `backup-cross-site` — no independent recovery site | 2 |

In a request, services are named inside their family:

```yaml
services:
  dns: default
  ntp: default
  identity: enterprise
  logging: protected-b
  backup: standard
```

## Implemented profiles by reference request

| Request | environment | security | assurance | availability | compute | storage | recovery | services |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `internal-development` | development | internal-baseline | standard | single-zone | small | standard | off | dns/ntp/identity/logging/backup |
| `internal-production` | production | protected-b-medium | standard | high | medium | high-capacity | standard | logging `protected-b` |
| `multi-tier` | production | protected-b-high | elevated | high | large | high-capacity | standard | logging `protected-b` |
| `recovery-enabled` | recovery | protected-b-medium | elevated | high | medium | high-capacity | standard | logging `protected-b` |
| `storage-heavy` | production | protected-b-medium | standard | high | small | high-capacity | standard | logging `protected-b` |

All five select region `east` and `logging: protected-b`, because the reviewed
inventory publishes only `site-01` (region `east`) and only a `logging-protected`
endpoint there.

## Changing this matrix

Adding an implemented profile requires a catalog entry, a resolver/validator path
and a regression. Promoting a deferred profile requires the missing realization
(native qualification, inventory or control mapping) to exist first; the deferred
status is the record that it does not.

Changing any profile in any way is a catalog revision: raise the `version` of the
profile that changed, raise the `version` of its catalog, and update this matrix.
A resolution, a desired state and a plan all bind the revision set, so the change is
visible in every derived artifact even when no request field changed.