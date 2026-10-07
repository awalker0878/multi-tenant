# P09 platform and capability expansion implementation

P09 development continues from `8b26bc81af3c3102b7d2d73653359bd0aae93f48`.
The current implementation is a set of executable expansion components. P09 and
G09 are **not complete**: the exact native tranche, selected enterprise effect
integrations, complete PostgreSQL qualification and receiving evidence remain open.
P07/P08 native acceptance and their outstanding software obligations remain unchanged.

## Delivered components

| Package | Implemented behavior | Limits and remaining scope |
| --- | --- | --- |
| P09.01 | VMware/AHV native power-on, shutdown, forced power-off and offline CPU/memory request adapters; strict plan/baseline/field checks; protected runtime selection | These five operations are the implemented adapter component scope. No native support is advertised. Additional selected operations need their own adapters and exact-tuple evidence. |
| P09.02 | Versioned tranche schema, complete eleven-dimension installed-profile bindings, six directed cross-platform routes and three same-family routes; separate Linux/Windows/appliance and five-method qualification plans | A row binds source, target, guest, data, policy, services, recovery, artifacts, topology and constraints. No reverse-route inheritance. Operator-selected real rows and native campaigns remain required. |
| P09.03 | PostgreSQL observation, no-change import, separate writer transfer, drift/uncertainty holds, field collisions across tenants, reconciliation and verified detach | Import makes no provider request and grants no write authority. The current independent owner protocol must prove old-writer exclusion. Native field collectors, writer fences and brownfield Q02/Q08 qualification must be commissioned for selected installations. |
| P09.04 | Dependency DAG, windows/blackouts, bounded duration, tenant fairness, tenant/endpoint/correlated-impact budgets, object serialization, pause/resume/stop, durable claims and separate reconciliation | Operation contracts cover HA, policy changes, patching, credential rotation, scale and relocation. Their selected native effects and service/policy/recovery observers are not supplied by a scheduler. The dispatcher port must be composed with those commissioned effects and enforced worker boundaries. |
| P09.05 | Real Ed25519 admission, exact capability/contract/artifact/installed-code bindings, protected trust and revocation, expiry, transition conformance and an operator guide | Packages select installed built-in implementations. They cannot inject code. Real signing custody, accepted versions and reviewed common-path/recovery transition evidence remain operating inputs. |

The adapter scope above records implemented behavior; it does not narrow R07,
R11, R20 or R26–R28, freeze ADR-022 or defer other requirements by developer fiat.
The [phase card](phases/p09.md) and [G09 criteria](gates.md#g09--platform-and-capability-expansion)
remain authoritative for the complete package scope.

## Architecture and authority

Planning owns tranche validation and directed qualification planning in
`services/planning/src/planning/domain/expansion.py`. Its matrix requires an exact
release/tranche/route record, accepted E3 level, current expiry and non-revoked
evidence before reporting native qualification. This computation is not a grant;
operational acceptance and write authority remain separate. The supplied conformance
fixtures contain no native qualification records.

Lifecycle owns the adoption journal, object/field claims, shared allocations,
enterprise operation records and control API. Migration `009_expansion.sql` runs
under the existing database owner; the runtime does not run migrations. Runtime
cannot delete event history. Object/field identity excludes tenant, application,
environment and profile identifiers so these cannot partition the same native claim.

The authenticated API is in `lifecycle.interfaces.expansion`. It delegates every
resource scope through existing Governance request authority. Wave creation accepts
immutable plan references. It does not accept client budgets, owner observations,
write grants, worker leases or allocation-release commands. The explicit
`lifecycle-expansion` process requires verified TLS and independently configured
owner ports. This does not automatically mount an uncommissioned API in an existing
native service deployment.

Workers use the existing native admission/current-authority and durable attempt
ledger. The new `platform_lifecycle` runtime entry selects a signed, statically
installed VMware or AHV adapter. Plan bytes and commissioning entries are rechecked
before effect boundaries. Native HTTP uses a pinned address, verified host/CA,
protected credential file, fixed route family, bounded body and response, and no
redirect/retry behavior. VMware requests use its session header. AHV mutations bind
the observed ETag and durable operation UUID; full VM updates preserve unowned fields.

An interrupted or rejected submission is held. A process restart, expired lease,
HTTP 404 or response loss does not authorize another mutation. Readback can establish
observed infrastructure state without establishing application readiness, native
writer exclusion, policy equivalence or operational acceptance.

## Safety and recovery behavior

- Adoption compares the proposed field values to independent current observations
  before import. Transfer checks the enumerated old writers, native exclusion,
  receiver, revision and epoch. Drift or uncertainty revokes local managed authority
  and retains claims. Reconciliation returns to an observation/import state;
  transfer is a separate action. Detach needs current exclusion and a different
  receiver, retains history and never deletes a VM.
- Enterprise dispatch reserves all pools atomically and serializes competing
  dispatchers. Active and unknown operations retain allocations and object claims.
  Budgets are rechecked at effect boundaries, including changed external usage.
  Pause/stop block subsequent native requests; already accepted effects require
  observation. Stop cannot be resumed. Independent final observation must bind the
  exact lease/specification, exclude the stale writer and preserve required policy,
  services and recovery before success and release are recorded.
- Package changes invalidate exact signed identities. Trust/manifest/key expiry or
  revocation prevents new requests. Upgrades and recovery require the exact old/new
  manifests, no active or unknown attempts, and reviewed common-path/recovery evidence.
  A version label alone does not carry support forward.

## Verification and commissioning

Run `python scripts/p09/qualify.py --output <directory>` with
`P05_POSTGRES_BIN` pointing at PostgreSQL 16's binary directory. The committed P09
GitHub workflow provides this dependency. The campaign runs all three affected
Python component suites, strict formatting/lint/type checks, wheel builds, schema
conformance and architecture validation, and retains source and log hashes.
Any skipped PostgreSQL check prevents a passing P09 qualification result.

The [partial local evidence](../../verification/p09/local/README.md) records
881 passing tests, 79 PostgreSQL skips and no test failures. Locked installs,
lint/format/type checks, wheels and schema checks pass. The architecture gate
passes after moving task-generated wheel-build source copies out of the checkout;
the original failure and check-order correction are retained. This partial result
does not pass the complete conformance campaign.

The local environment has no PostgreSQL binary and cannot change to the unprivileged
database account. Installing PostgreSQL failed at the environment's setuid/setgroups
boundary. Local runs therefore retain the PostgreSQL skips as unexecuted obligations.
Automatic approval review rejected publishing the prepared branch; hosted verification
has not run for this source. See the [review packet](p09-completion-review.md) and
[operating guide](../operations/runbooks/platform-expansion.md).

## Native API references

The adapter implementation uses the following primary API contracts. These references
establish request shapes, not support for an installed platform release:

- [VMware power start](https://developer.broadcom.com/xapis/vsphere-automation-api/latest/api/vcenter/vm/vm/power__action%3Dstart/post/)
  and [CPU update](https://developer.broadcom.com/xapis/vsphere-automation-api/latest/api/vcenter/vm/vm/hardware/cpu/patch/).
- [Nutanix VMM v4.0 VM API](https://developers.nutanix.com/api/v1/sdk/namespaces/main/vmm/versions/v4.0/languages/python/ntnx_vmm_py_client.api.vm_api.html)
  and [native update example](https://www.nutanix.dev/2025/11/25/updating-vms-with-the-nutanix-v4-apis-and-powershell/).
  This implementation retains TLS verification and does not adopt insecure example options.

No claim is made that a documented latest API is the installed or qualified version.
Exact API/backend/network/storage/guest observations are required for each tranche.
