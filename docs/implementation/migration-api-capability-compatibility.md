# Migration API capability compatibility — version tolerant, fail closed

Branch: `codex/capability-runtime-assurance-audit-fixes` (PR #64).
This increment is an **E2 engineering implementation**. It does not certify
VMware, OpenStack or Nutanix native installations or independently accept a
production migration.

## Policy and native admission

A platform release is not an admissibility proxy. The approved source and
destination installations may expose **different API families, versions,
microversions and entitlements**. A migration is compatible if the actual
required operations can be exercised on a negotiated version available in
their respective installations and carry current independent Assurance E3
qualification. An E4 receiving decision is a separate operating gate.

The migration route owns a bounded, immutable `api_usage` list; each item has
a stable `capability_id`, the `source`, `target` or `both` side,
`criticality` (`critical` or `optional`) and a reason/impact statement.
The route digest, Assurance route qualification and plan recipe all bind this
list. Endpoints and vendor method names are implementation details; absence
of a feature from a particular version never makes a different API release
unsupported without testing that other negotiated release.

Some example code-level tags:

| Migration mechanism | Source code family | Stable capability |
| --- | --- | --- |
| VMware snapshot/lease export | `workers/lifecycle/.../vmware_export.py` | `vm.disk.export` |
| OpenStack Nova/Cinder snapshot/image capture | `workers/lifecycle/.../openstack_capture.py` | `vm.disk.export` |
| AHV v4 image capture | `workers/lifecycle/.../ahv_capture.py` | `vm.disk.export` |
| VMware OVF/NFC target | `workers/lifecycle/.../vmware_import.py` | `vm.disk.import` |
| OpenStack Glance target | `workers/lifecycle/.../openstack_image_import.py` | `vm.disk.import` |
| AHV image/VM target | `workers/lifecycle/.../ahv_destination.py` | `vm.disk.import` |

`scripts/assurance/test_migration_api_usage.py` verifies that these tags
remain in real modules. This is an initial static coverage sample, **not**
complete discovery of every native call site, host environment, security
policy, guest requirement or use of an optional capability.

## Environment-specific evidence (do not confuse with documentation)

The environment-specific record is keyed by **installation ID and immutable
profile digest**. Each side advertises independently negotiated
`api_family -> [version]` values and an entitlement decision per feature.
Observations retain an API family and **one exact version**, source
(`spec_diff`, `live_probe`, `contract_test` or `operator`), timestamp,
expiry, result, evidence checksum and current qualification decision.
Each supported API candidate must also be available in the installed version
list and entitled for the caller.

- Spec and contract claims cannot independently grant positive E3 support.
- Expired, missing, cross-installation, ambiguous, revoked, unsupported or
  unentitled operations do not pass.
- A qualified observation against **one** API version can be selected even
  if an older version on the same installation lacks the feature. The exact
  selected API family/version is returned for traceability.
- If the selected version becomes unavailable, a subsequent read and native
  admission must be held; a newer version does not inherit the old proof.
- API version metadata is described by
  `contracts/schemas/capabilities/api-version-record-v1.json`: product
  release, per-family/version, release/deprecation/sunset dates, official spec
  URL/checksum and changed/removed semantic capabilities. Unknown dates or
  missing specifications must be recorded as null/unknown, not invented.

Planning calls Assurance over the **existing service-authenticated boundary**
to obtain these records. Assurance returns `api_evidence` only when its
independent native resolver verifies the separately recorded
`migration.api_records` capability, including a binding digest covering
caller scope, tranche/release identities and the complete API evidence object.
That signature and runtime evidence are independent of the operator's
specification catalogue. The actual native probe producer and operating
installations must still be commissioned.

## What blocks, what generates warnings

| Classification | Consequence |
| --- | --- |
| Critical / qualified on a negotiated version | Eligible at the API layer (all other native/receiving gates remain) |
| Critical / absent, unsupported, unentitled or unknown | **Blocked** — no migration approval or effect; show the exact missing requirement |
| Optional / available | Eligible; no omission |
| Optional / unavailable or degraded | **Conditional** — visible administrator warning, cannot proceed silently |
| Optional / independently accepted omission | API layer can become eligible but continues showing an impact warning and omission marker |

Structural disk export/import, boot, power, data, encryption/isolation,
necessary network paths and recovery cannot be relabeled `optional` to
bypass safety. A *particular* nonessential firewall setting may be omitted
only if its loss neither alters a required application flow nor weakens
required ingress/egress and tenant isolation checks. Required firewall
behavior remains a hard admission condition independently verified at the
native effect boundary.

Optional omission acceptance is bound to the exact route, tenant,
application, environment, capability and side, and requires **E4** evidence
from the independently reviewed Assurance record, including a separate
`effect_suppressed_sha256` witness identifying the affected native effect
that is actually omitted. A mere administrator acknowledgement or declared
missing endpoint cannot stand in for suppression evidence. The site console shows
blocking versus optional warnings, their impact, and the observed API
release per feature. It does not issue approvals and cannot self-assert
an E4 omission. An E3 route-level record without per-feature evidence
cannot silently grant optional omission.

## Current engineering and commissioning gaps

- The E2 evaluator, authenticated support read, directional status gate,
  strict admin alerts, three-platform disk call-site tags and negative tests
  are implemented. Source-bound hosted checks must still pass.
- **The existing deployed route tranches have not yet all been augmented
  with code-derived API usage.** An undeclared v1 route retains its existing
  exact-tuple Assurance policy; migrate every commissioned route to reviewed
  `api_usage` before asserting that API-by-API coverage is complete.
- Approved native per-feature *create → read → cleanup* probes must be
  implemented for every selected capability and API version. Failed or
  ambiguous write effects require custody reconciliation before retry.
- Operator licensing/entitlement observations, release/extension
  inventories, owner cleanup, current API version readback, production
  alert delivery, E4 omission approval workflow, and version pinning in
  the persisted native effect grant remain **open**.
- A qualified alternative adapter for an unsupported critical capability
  remains a separate evidence/implementation work item; do not infer it
  from a doc or arbitrary mapping. Until reviewed the migration is blocked.
- Ensure the next release controls can reject any unknown critical API
  requirement in *all* routes, including those not yet carrying
  `api_usage`. No native support follows solely from this increment.

The authoritative remaining-work queue is [`next_work.md`](../../next_work.md);
the native assurance acceptance record remains
[`capability-runtime-assurance-ledger.md`](capability-runtime-assurance-ledger.md).
