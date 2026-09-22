# Supported service-profile matrix

Every profile below is reviewed in `profiles/<family>/catalog.json`. Status
`IMPLEMENTED_INTERNAL_IPV4_OZ_RZ` means a request in this repository may select it;
`DEFERRED_NOT_IMPLEMENTED` means selection is refused with `UNSUPPORTED_PROFILE`.

There is exactly one implemented realization: **internal IPv4, operations zone plus
restricted zone**. Everything outside that shape is declared and deferred so the
refusal is explicit rather than accidental.

## Environment

| Profile | Rank | Status | Requires |
| --- | --- | --- | --- |
| `development` | 1 | implemented | assurance ≥ 1, availability ≥ 1, security ≥ 1, recovery off |
| `test` | 2 | implemented | assurance ≥ 1, availability ≥ 1, security ≥ 1, recovery off |
| `qualification` | 3 | implemented | assurance ≥ 1, availability ≥ 1, security ≥ 1, recovery off |
| `production` | 4 | implemented | assurance ≥ 1, availability ≥ 2 (`high`), security ≥ 2, recovery on |
| `recovery` | 5 | implemented | assurance ≥ 2 (`elevated`), availability ≥ 2, security ≥ 2, recovery on |

## Security

| Profile | Rank | Status | Service class |
| --- | --- | --- | --- |
| `internal-baseline` | 1 | implemented | `standard` |
| `protected-b-medium` | 2 | implemented | `protected-b`, distributed firewall |
| `protected-b-high` | 3 | implemented | `protected-b`, dedicated edge context, native load balancer |

All three declare `public_ingress: false` and `internet_egress: false`.

## Assurance

| Profile | Rank | Status | Requires |
| --- | --- | --- | --- |
| `standard` | 1 | implemented | `audit_logging`, recovery not required |
| `elevated` | 2 | implemented | `audit_logging`, `dedicated_edge_context`, recovery required |
| `regulatory` | 3 | **deferred** | no reviewed control mapping or native evidence model |

## Availability

| Profile | Rank | Status | Zones |
| --- | --- | --- | --- |
| `single-zone` | 1 | implemented | `OZ` |
| `high` | 2 | implemented | `OZ`, `RZ` |
| `maximum` | 3 | **deferred** | `OZ`, `RZ`, `PAZ` — only OZ/RZ compositions exist |

## Recovery

| Profile | Rank | Status | Requires |
| --- | --- | --- | --- |
| `standard` | 1 | implemented | `RZ`, `backup` service |
| `enhanced` | 2 | **deferred** | independent recovery site — no such inventory exists |

## Compute

| Profile | Rank | Status | Guest |
| --- | --- | --- | --- |
| `small` | 1 | implemented | 2 vCPU / 4 GiB / 40 GiB boot |
| `medium` | 2 | implemented | 4 vCPU / 8 GiB / 60 GiB boot |
| `large` | 3 | implemented | 8 vCPU / 16 GiB / 80 GiB boot |
| `gpu` | 4 | **deferred** | no reviewed accelerator capacity or scheduling model |

## Storage

| Profile | Rank | Status | Requires |
| --- | --- | --- | --- |
| `standard` | 1 | implemented | boot disk only |
| `high-capacity` | 2 | implemented | boot disk plus a 100 GiB protected data volume |
| `encrypted-high-capacity` | 3 | **deferred** | key custody and encryption qualification are not implemented |

## Network

| Profile | Rank | Status | Requires |
| --- | --- | --- | --- |
| `internal-ipv4` | 1 | implemented | IPv4, `/27`, offset gateway host 1 |
| `dual-stack` | 2 | **deferred** | routed IPv6 — the lab is an experiment, not a placement authority |
| `ipv6-only` | 3 | **deferred** | no qualified IPv6-only native path |

## Placement (region)

| Profile | Rank | Status | Requires |
| --- | --- | --- | --- |
| `east` | 1 | implemented | reviewed inventory in region `east` |
| `west` | 2 | implemented | reviewed inventory in region `west` |
| `public` | 3 | **deferred** | no public or partner exposure path is implemented |

A region profile is a filter over reviewed inventory, not a capacity promise.

## Service

| Profile | Rank | Status | Required binding class |
| --- | --- | --- | --- |
| `dns/default` | 1 | implemented | `dns-internal` |
| `dns/external-view` | 2 | **deferred** | `dns-external` — public name publication is out of scope |
| `ntp/default` | 1 | implemented | `ntp-internal` |
| `identity/enterprise` | 1 | implemented | `identity-directory` |
| `identity/standalone` | 2 | **deferred** | `identity-standalone` — contradicts the reviewed identity boundary |
| `logging/standard` | 1 | implemented | `logging-standard` |
| `logging/protected-b` | 2 | implemented | `logging-protected` |
| `backup/standard` | 1 | implemented | `backup-isolated` |
| `backup/enhanced` | 2 | **deferred** | `backup-cross-site` — no independent recovery site |

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