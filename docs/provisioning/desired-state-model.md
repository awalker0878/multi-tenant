# Internal desired-state model

Resolved desired state is the boundary between portable intent and platform
realization. It is fully resolved (no remaining `auto`), fully expanded (every
domain and workload enumerated) and carries no native mutation.

Builder: `provisioner/compiler/desired_state.py`
Model: `provisioner/domain/desired_state.py`
Schema: `provisioner/schemas/v1/resolved-desired-state.schema.json`
Format: `hosting-resolved-desired-state/1`
Status: `RESOLVED_DISABLED_NOT_AUTHORIZED`

Examples: [`examples/resolved/*.desired-state.json`](../../examples/resolved).

## Fields

| Field | Content |
| --- | --- |
| `format`, `status` | artifact identity and the disabled/unauthorized marker |
| `request_digest` | identity of the request this state came from |
| `apiVersion`, `kind` | carried through from the request |
| `tenant`, `wsd`, `owner`, `environment` | identity and lifecycle |
| `site`, `platform`, `platform_family`, `trust`, `service_class` | the placement result |
| `profiles` | the flat resolved profile map (with a nested `services` map) |
| `profile_versions`, `catalog_versions`, `catalog_digest` | the reviewed revision of every resolved profile, of every catalog, and the canonical digest of the whole reviewed catalog set |
| `policy` | the policy summary: rules evaluated, violations, exceptions |
| `placement` | the full `PlacementDecision`, including rejected candidates |
| `capabilities` | the resolved capability requirements |
| `services`, `service_bindings` | the declared service handoffs |
| `reservations` | per-zone capacity reservations |
| `clusters` | the selected cluster records |
| `domains` | one `DomainIntent` per zone, each with its `workloads` |
| `native_contact` | always `false` |
| `digest` | canonical SHA-256 over the document without `digest` |
| `limits` | the standing non-claims |

### `domains[]`

One entry per zone (`OZ`, and `RZ` when `availability` above `single-zone`):

| Field | Content |
| --- | --- |
| `id` | the deterministic domain identity |
| `zone` | `OZ` or `RZ` |
| `cell`, `cluster` | the selected native placement: the cell is the one placement chose for *this* zone inside the coherent envelope, and the cluster is resolved only inside that cell |
| `prefix` | the allocated prefix for this zone |
| `gateway_host_number` | the offset gateway inside the prefix |
| `inputs` | the platform inputs the compiler consumes |
| `workloads[]` | `name`, `address`, `vcpu`, `memory_gib`, `boot_disk_gib`, `data_disk_gib`, `inputs` |

The current corpus resolves **one workload per zone**, so one plan carries four
native subjects.

## Digest

`finalize()` renders the document, drops `digest`, and hashes the canonical JSON.
Any change to any field changes the digest, which is what makes the golden corpus
a real regression rather than a snapshot of formatting. Because the document
carries the reviewed revision set, a profile or catalog revision changes the
desired-state digest and the plan identity even when no request field changed.

## What this artifact is not

It is not a deployment, not a reservation confirmation and not an authorization.
Capacity, addresses and service bindings are **declared**, not confirmed by their
owners. Native qualification and separate production authorization remain required
before anything is applied.