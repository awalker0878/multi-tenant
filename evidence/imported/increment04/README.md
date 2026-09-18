# Portable Secure Hosting — Implementation Increment 04

**Native readback and interrupted-change recovery triage.** This builds on
Increment 03 without changing the architecture, the ten native Terraform
module/root pairs, or the DNS and routed service-identity implementations.

## Current boundary

The new [NSX reader](tools/nsx_observe.py) and [Nutanix reader](tools/nutanix_observe.py)
are **candidate native integrations**. Their actual HTTPS and failure handling was
exercised against a disposable localhost fixture with documented response shapes,
not a vendor appliance. The [recovery reviewer](tools/recovery_review.py) is an
**offline engineering check**, not a hosting controller, authorization service,
automatic retry engine or rollback tool. All three preserve apply/delete/activate
as false.

**No user/vendor infrastructure was contacted. Terraform remains unavailable.**
The binary retry failed because the container could not resolve the official release
host. Actual Terraform initialization, validation, provider schemas, locks and
mocked plans remain blocked/not-run. Python and packet passes do not replace them.

## Start here

[Execution guide](Implementation_Execution_Guide.docx) ·
[Native readback procedure](docs/NATIVE_READBACK.md) ·
[Interrupted-change recovery](docs/INTERRUPTED_CHANGE_RECOVERY.md) ·
[Commissioning](docs/COMMISSIONING.md) ·
[Implemented scope](docs/IMPLEMENTATION_SCOPE.md) ·
[Remaining work](docs/NEXT_WORK.md)

## What is new

| Integration | Reads and checks | Excluded scope |
|---|---|---|
| NSX Local Manager | Exact segment, Tier-1, static route, group, gateway/security policy; config revision before and after a separate intent-status GET; exact intent version and enforcing-system coverage | Global Manager, project-root variants, refresh POST, effective rules on every transport node, resource creation or release of quarantine |
| Nutanix networking/prism v4.3 | Exact VPC/subnet and strong ETag; known single task before and after resource reads; operation/time/entity scope and completion | VMs, route/security-policy readback, composite/batch task expansion, task cancellation, inferred task IDs or API-version fallback |
| Recovery triage | Bound report history, freshness, generations, recorded writer fencing, quarantine and containment; re-evaluates the observation rather than trusting its final label | Real fencing, approval-signature verification, state unlock/import, task replay, data deletion and activation |

A completed native task is not necessarily matching configuration. Matching
configuration is not necessarily current realization. Aggregate realization is
not packet-path or full ZIP proof. The tools deliberately retain these distinctions.

## Run locally

Check release hashes **before** refreshing quality records:

```sh
python tools/check_release.py
python tools/check_local.py
python lab/run_readback_lab.py --execute
python lab/run_dns_lab.py --execute
python lab/run_namespace_lab.py --execute
python tools/check_package.py
```

The new readback campaign uses real loopback HTTPS, temporary certificates and
scripted published response shapes. It performs GETs only. Fence/quarantine records
in that fixture are simulated, not native control evidence. The DNS and routed
IPv4/mTLS campaigns retain their existing limits. Their counts are not additive
unique unit-test coverage. The runtime dependencies and Linux namespace requirements
remain in `requirements-runtime.txt`, `requirements-test.txt` and [lab notes](lab/README.md).
No private keys, provider plugins or toolchain binaries are shipped.

## Native read-only observation

The following first command validates a disabled example **without contact**:

```sh
python tools/nsx_observe.py examples/nsx_observation.json.example
python tools/nutanix_observe.py examples/nutanix_observation.json.example
```

For an accepted native target, use separately controlled expectation records and a
new private output. Credentials are injected as `NSXT_USERNAME` / `NSXT_PASSWORD`
or `NUTANIX_USERNAME` / `NUTANIX_PASSWORD`; never put values in arguments or chat.

```sh
python tools/nsx_observe.py /secure/nsx-expected.json \
  --read-authorized-target --expected-origin https://nsx.site.invalid \
  --ca-file /secure/approved-ca.pem --output /secure/nsx-readback-unique.json
```

The `.invalid` address is intentionally unusable; it must not be treated as an
actual endpoint. Native contact additionally requires `contact_enabled: true`,
exact matching origin and accepted native identities/version tokens. Consult the
procedure before enabling it. No redirects, environment proxies, response links,
resource discovery, native writes or fallback API versions are followed.

## Interrupted changes

```sh
python tools/recovery_review.py /secure/accepted-readback-manifest.json \
  /secure/native-readback.json /secure/interrupted-change-context.json \
  --output /secure/recovery-review-unique.json
```

`READY_FOR_OPERATOR_RECOVERY_REVIEW` means the supplied records are consistent for
operator review. It is never permission to apply, delete, cancel a task, release
quarantine or activate a service. Digest equality is not signature or approver
verification. A stopped runner is not proof that delayed native tasks stopped.
Missing task identity, stale observations, unverified writer fencing or active
containment remain explicit holds. No automatic rollback is implemented.

## Evidence and lineage

[Local regressions](quality/local_validation.json) ·
[Readback fault campaign](quality/local_native_readback.json) ·
[DNS campaign](quality/local_dns_transactions.json) ·
[IPv4 routing/mTLS campaign](quality/local_packet_lab.json) ·
[Terraform gate](quality/terraform_validation.json) ·
[Download attempt](quality/toolchain_access.json) ·
[Package checks](quality/package_validation.json)

`quality/increment01/`, `increment02/` and `increment03/` are historical.
[Increment03 fingerprints](sources/increment03_manifest.json) preserve the immediate
baseline. `reference/` and `terraform/` remain byte-for-byte unchanged; no workbook
recalculation or native provider qualification is claimed.

Use `python tools/verify_terraform.py --mock-tests` only in a separately approved
connected toolchain with trusted plugins. It validates/mocks plans only; it never
performs a native apply. The actual firewall, platform tuple, API behavior, identity
scope, IPAM and service acceptance must still be resolved before deployment.
