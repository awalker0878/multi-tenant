# First native reference-service commissioning kit

**Record:** NRC-M01 · **Version:** 0.1 · **Status:** Proposed.<br>
**Responsible roles:** hosting solution architect and the relevant infrastructure owners.<br>
**Actual site, platform/edge selection, native execution and approval:** not supplied.

This is a new engineering and operating elaboration of [SOL-M01](../../current/internal-hosting-solution.md),
[ICD-M01](../../current/interface-agreements.md), [the B14 build sequence](../../solutions/internal-protected-workload/9-build-sequence-with-explicit-acceptance-dependencies.md)
and [the W14 assertions](../../solutions/internal-protected-workload/13-verification-assertions-and-actual-evidence.md).
It does not replace those records, recover a missing Word original, or reopen the
resolved documentation-model audit. It introduces no new hosting controller or API.

## What the first service must exercise

Retain the source's **two tenants, each with independent OZ and RZ instances**, the
explicit tenant/domain security-edge handoffs, controlled service consumption and
separate management/OOB authority. Reuse the [actual worked schedules](../../solutions/internal-protected-workload/README.md)
as design fixtures; do not copy their example IP addresses into a live allocation.
Public ingress and Internet egress stay outside this internal reference offer.

The native platform, firewall/context implementation and each actual client of DNS,
time, identity, keys, storage, backup and telemetry must be selected in the site design.
A successful source check or provider-mocked plan cannot make those selections.
IPv4-only and dual-family stages must be distinguished. The merged
[routed IPv6 laboratory](../routed-ipv6-lab.md) now adds actual Linux packet-path
observations to the earlier model and loopback tests. That local fixture still does
not qualify a native dual-stack offer or choose the site's offered family.

## Use the kit in this order

| Working document | Deliverable |
| --- | --- |
| [Site inputs and ownership](site-inputs.md) | An actual, controlled engineering input for every blocking decision |
| [Native realization sequence](platform-build.md) | Separate Nutanix, VMware/NSX and OpenStack build responsibilities and readback limits |
| [Foundation-service interfaces](service-interfaces.md) | Actual client/producer/path/entitlement and failure terms, not generic service flags |
| [Campaign and observation method](campaign.md) | Healthy controls, native observation sources and per-attempt records for existing W14 assertions |
| [Recovery, rollback and retirement](recovery-retirement.md) | Useful-data restore, writer exclusion, safe stops and surviving retention obligations |

The [planning register](../../../sources/commissioning/native_reference_plan.json)
contains 22 input questions, eleven work-package steps and twelve W14 run-sheet groups.
These are **planning entries**, not new independent tests or executed results. The
original CT/RA/W14/Q11 associations remain in their existing source register.

## Export a NEW local working copy

From repository root:

```sh
python scripts/commissioning_pack.py check
python scripts/commissioning_pack.py draft --output /secure/campaigns/reference-service-01
```

The parent directory must already exist in an approved, trusted local workspace
**outside the Git checkout**. The destination must not exist or traverse symlinks.
The exporter creates private files on a supporting POSIX filesystem, never overwrites
a previous run, and leaves an incomplete manifest if writing is interrupted. Protect
actual completed records according to their classification and retention rules;
filesystem mode bits are not a complete evidence-custody system.

The output includes `engineering-inputs.csv`, `work-package-runs.csv`,
`observation-attempts.csv`, a README and source/exporter digests. The observation
worksheet separately captures direction, operation and observer identity by reference,
not a credential value. The site values,
owner assignments, credentials, timestamps, native IDs, results and evidence are not
invented. Initial results are NOT_RUN and input reviews are UNREVIEWED. Duplicate
observation rows deliberately for each actual attempt/family/placement/variant; assign
unique attempt IDs under the approved campaign record.

`check` returns zero only for a consistent **planning package**. `draft` returns zero
only for completed local export. Neither reads a native API, runs Terraform/Ansible,
checks real approvals, validates completed evidence, or grants apply/delete/activation.
A manifest digest binds bytes; it does not identify an approver. No CI job exports or
collects actual site values.

## Source and delivery boundary

The initial review kit used PR #12 as its source basis. This revision was reconciled
with main `2a1231644f3ea0dc176616d54c584717730b7468` after PR #13, from an
exact Git-tree-verified source snapshot. It retains all routed IPv6 source, workflow
and navigation. The current kit's exact CI run is a separate record; earlier passing
main checks are not substituted for it, and no native results are supplied. New proposal text is separated here from the frozen
source chapters. Existing native modules, observer implementations, provider pins,
lockfiles, source documents and decisions are unchanged by this kit.

The old [increment backlog](../../../sources/implementation_backlog.csv) remains a
historical increment record, including its former toolchain blocker. Consult the exact
current commit checks and [the engineering allocation](../assertion-allocation.md)
for current software scope. The site-selection, security-edge, IPAM, key/protection,
native observation and activation obligations are not closed by this export.

[Implementation index](../README.md) · [Current design workspace](../../current/README.md)

## Integration audit in this revision

The planning graph now represents G1 explicitly at NC20 and requires it, G0/G2 and
applicable initial G4 before the separate production-review stage. Required B14
responsibilities cannot disappear merely by removing a gate label. Cleanup depends
only on the reviewed owner/scope record: failed bootstrap, installation or denied-domain
creation does not have to succeed before its actual partial effects can be reconciled.
These are planning consistency checks, not executable authorization decisions.

The documentation generator also retains the existing IPv6 engineering and execution
links. Regenerating navigation must not silently remove a concurrently merged work package.
