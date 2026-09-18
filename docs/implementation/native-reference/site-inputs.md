# Site input package and resource ownership

**NRC-M01 supporting procedure — Proposed.** Actual entries and adoption remain unrecorded.
Parent: [P0–P6 handoff responsibilities](../provisioning-strategy/1-provisioning-scopes-ownership-and-accepted-handoffs.md).

## 1. Establish the bounded service

Keep architectural adoption, authorization to run a restricted qualification fixture,
acceptance of offered capacity, and authorization of a production workload as different
records. Record the selected site/cell, permitted data and fault scope, actual platform
and security-edge tuple, address families, co-residency and service promises. Do not use
a product-family name or a Protected B label in place of the actual engineering release.

The worksheet input IDs are practical collection points, not new requirement IDs:

| Decision group | Input IDs | Required engineering content |
| --- | --- | --- |
| Scope and responsibility | SITE, PLATFORM, EDGE, FAMILY, OWNERS, ACCEPTANCE | Actual site and tuple, offered functions, supported operations, owner scopes and real review references |
| Commissioned foundations | BOOTSTRAP, MANAGEMENT, FABRIC, IPAM | Recoverable trust, OOB/management independence, physical inventory, attachment pools, routing authority and owned allocations |
| Endpoint initialization | DNS, TIME, IMAGES, PLACEMENT | Actual resolver/registration/DHCP/metadata clients, selected time profile, accepted image/boot modes and eligible pools |
| Data and protected service use | IDENTITY, KEYS, STORAGE, BACKUP | Consumer identities, endpoint versus object entitlement, copy ownership, native capture/transfer and independently recoverable custody |
| Operating capability | TELEMETRY, CAPACITY, RECOVERY, RETENTION | Attributable collection, surviving measured limits, eligible isolated recovery, writer exclusion and retained-copy obligations |

Each `controlled_record_reference` points to the actual protected record. Do not fill
it with credentials, a Terraform state dump or an inline production inventory. The
`assigned_owner` is populated by the real responsible organization; the role label in
this repository is not evidence that someone accepted the work.

## 2. Distinguish installation from an offered service

P0 provides authorized bootstrap dependencies; P1 supplies accepted transport and
physical attachments. P2 platform installation may use P0 services while P3 installs
permanent service components. Their joint acceptance follows the required restricted
observations. This breaks the installation dependency cycle without declaring an
unqualified platform to be available for ordinary tenant placement.

For every handoff, obtain identity/version, offered scope, capacity/failure basis,
dependencies, observed readiness and lifecycle rules from the producing owner. The
consumer confirms that its requirement is met. A reference string in a local CSV is
not a signature, current lease, or authentication of that acceptance.

## 3. Bind one owner to each native object

The platform owner controls the native domain, subnet/segment/router, workload and
owned mandatory policy scopes. The security-edge owner controls ZIP contexts, routing
and inspection. Address/name, identity/key, data/protection and telemetry owners control
their services. Foundation changes remain with network/hardware and management owners.

Record create/update/import/replace/delete/uncertain-outcome support for each operation,
not just which provider can create an object. Name the observing identity separately
where independent readback is required. Do not give one routine runner all foundation,
security-edge, tenant and workload privileges merely to simplify the work package.

## 4. Review capacity under one explicit failure basis

Measure the selected physical/virtual components with the actual inspection, encryption,
logging and transfer modes enabled. Capture existing commitments, reservations, temporary
probe demand, rebuild/restore load and remaining safe capacity in their own units.
Check eligible hosts/storage, attachment/context slots, routes/policy objects, sessions,
throughput, telemetry ingest/storage and relevant API/job limits independently.

Do not sum CPU, bandwidth and firewall sessions into one number. Do not count received
but uncommissioned equipment, the same reservation twice, or ineligible hosts as spare
capacity. Record which failure is covered and what is shared: a site label is not proof
of independent power, identity, keys, storage, control or security-edge services.

## 5. Stop on unresolved engineering, not on missing cosmetic fields

An unresolved mandatory endpoint, support limit, owner, real route, protocol, recovery
requirement or retention condition blocks the corresponding native activity. A missing
optional formatting field is different. The exporter intentionally does not decide
which exception or acceptance a real authority can issue.

Complete the actual project LLD and interface records through the controlled review
process. Then select the applicable assertions from the [maintained allocation](../assertion-allocation.md)
and [verification families](../../assurance/verification-families.md). Site applicability
is not supplied by this generic kit, and a not-applicable decision needs its own accepted
rationale rather than an empty test result.

[Kit index](README.md) · [Platform sequence](platform-build.md)
