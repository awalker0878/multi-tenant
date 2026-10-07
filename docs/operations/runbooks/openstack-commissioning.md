# OpenStack commissioning and P07 input review

Owners: SRE/platform, Infrastructure, security, service and qualification owners.
Scope: P07.01 and preparation for P07.02–P07.06; Q05/Q06 and G07.

The [P07 card](../../implementation/phases/p07.md) requires an actual selected
installation, separately bounded native campaign, P01 operating controls and G06
receiving. Development authorization permits preparation. It does not provide
installed facts, credentials, third-party ownership or a native campaign grant.
Use the [canonical register](../../implementation/delivery-register.yaml) for
receiving decisions and [operating inputs](../../../release/operating-inputs.json)
for OP01–OP07. No additional baseline/G00 approval is requested.

## Collect and validate deployment inputs in Console

Use the [API-first configuration workflow](../../implementation/openstack-version-qualification.md)
to select approved source/destination connections and pull configured options and
features. Save the API findings with administrator validation, reasoned overrides,
and remaining manual references. Configuration is stored by Inventory, not by
editing the repository's all-unknown commissioning template. Native credentials
remain protected. A confirmed review supplies input provenance; E3 observations,
current authority and independent native acceptance must still come from their
actual owners. Missing runtime inputs do not block product development.

## Collect the commissioning packet

The repository's [input record](../../../release/p07-native-inputs.json) records
only supplied observations; unknown values remain null. Actual endpoints, native
data, credential material and original evidence stay in the protected operating
record. Populate a protected copy when it contains identifying operating facts.
Never put passwords, private keys, tokens, Terraform state or saved-plan bytes in
the repository or general CI artifacts.

| Input | Required contents of the protected record | Responsible owner | Cases |
| --- | --- | --- | --- |
| N01 | Installed distribution/release, exact service APIs/microversions, hypervisor/network/storage backends, project/region and failure domains; independent current native observation | OpenStack platform | Q05.01/.03 |
| N02 | Campaign ID, exact tenant/application/site/endpoints, named resources/datasets, permitted effects, impact/concurrency quotas, time window, cleanup owner and separate retirement boundary | Platform/security | Q05.01 |
| N03 | Approved endpoint allowlist and TLS trust, restricted writer and separate read identities, credential references, permission visibility and independently observed scope/denials | Security/IAM | Q05.01/.08 |
| N04 | Exact Terraform executable, providers, dependency lock, modules and worker artifact; saved-plan digest; backend/workspace/lineage/serial; lock/fencing and independent state-recovery custody | Infrastructure/state | Q05.03/.08 |
| N05 | Sole writer for each resource/field, externally owned resources, imports/adoption, independent mapping and drift comparison | Infrastructure/resource | Q05.03/.09 |
| N06 | Approved image/profile digests, firmware/device/boot/storage/network constraints, hardening and reproducible application configuration | Guest/application | Q05.04 |
| N07 | Quarantine, traffic activation mechanism and approved Q06 expected outcomes across same-host/subnet, inter-host and edge; applicable IPv6 and return paths | Network/security | Q05.04/.07 |
| N08 | Native quotas and authoritative capacity/IP/service allocation interfaces; scoped reserve/confirm/reconcile/release receipts and partial-success rules | Allocation/service | Q05.02 |
| N09 | Versioned IPAM/DNS, identity, time/trust, logging, monitoring and backup interfaces; authoritative owners and access, health/reply checks and uncertain-outcome behavior | Enterprise service | Q05.05 |
| N10 | Approved synthetic database/attachment manifest, accepted restoration objectives, isolated restore destination, key/data custody and loss/reconciliation procedures | Backup/application | Q05.06/.08 |
| N11 | Actual scoped stop/revocation rehearsal, stale-worker exclusion, boundary authority checks, accepted/unknown effect reconciliation and response owner | Lifecycle/security | Q05.01/.08 |
| N12 | Separate retirement authority, explicit owned deletion set, legal/retention decisions, retained data/keys, independent absence checks before allocation release | Governance/retention | Q05.10 |
| N13 | Named independent observer/reviewer access, artifact custody and retention, original failure preservation, exact tuple/operation support review and expiry | Qualification/Assurance | Q05.01/.10 |
| N14 | Actual applicable G06 receiving decision and OP01–OP07 operating-control records from their existing authorities | SRE/receiving | Q05.01 |
| N15 | Application service checks, dependency readiness, data/metadata/attachment comparisons and mandatory activation/hold criteria | Application/security | Q05.06/.07 |

Bind the packet to one `scope` with P05's exact tenant/site/environment/resource/
endpoint/native-scope fields, one campaign ID and expiry. The binding contains
SHA-256 identities for the plan, installed tuple, artifact set, ownership map,
toolchain, state binding, service contracts, impact budget and data scope. These
hashes identify protected contents; supplying a hash does not verify those contents.
Use P05's `p05-json-v1` canonical JSON for structured-material digests.

Each supplied cell records actual owner/observer identities, observation and expiry
times, immutable `evidence://` references with digest/revision/level, the exact
binding digest, and an attributable independent review. Timestamps are UTC Unix
seconds. N01, N03 and N11 require actual E3/E4 observations: P06 simulation cannot
stand in for installed facts, scope checks or native stop/revocation. An unknown
cell cannot carry observations or approvals. Complete evidence remains subject to
independent retrieval, identity verification and current authorization.

## Run the local check

From the repository root after the locked Lifecycle installation:

```sh
uv sync --project services/lifecycle --locked
uv run --project services/lifecycle --frozen python -m lifecycle.bootstrap.commissioning \
  --input release/p07-native-inputs.json --require-complete
```

Exit 0 means structurally valid (or complete when strict mode is selected); exit 1
means invalid/unreadable input; exit 2 means a valid incomplete strict-mode record.
Output lists stable input IDs, responsible roles and affected packages/cases without
echoing evidence locations, identity values or native facts. Duplicate JSON keys,
nonfinite numbers, oversized/nonregular inputs, unbound evidence, wildcard scope
and contradictory claims are rejected. Missing, expired, rejected or unreviewed
inputs remain held. The tool makes no network call and reads no credentials.

Even a complete packet returns `native_write_authorized: false` and
`native_qualification_established: false`. It cannot be used as a grant, execution
adapter, scope proof or published support claim. There is no native runtime adapter
in this increment; P06 remains an isolated simulation.

## Compare the reviewed saved plan

The second local command compares the P05 immutable envelope with the protected
commissioning record, supplied toolchain/state/ownership observations and actual
saved-plan file bytes:

```sh
uv run --project services/lifecycle --frozen python -m lifecycle.bootstrap.native_preflight \
  --plan /protected/plan-envelope.json \
  --commissioning /protected/p07-native-inputs.json \
  --toolchain /protected/toolchain.json \
  --snapshot /protected/independent-snapshot.json \
  --saved-plan /protected/reviewed.tfplan
```

The envelope contains exactly P05 `content` and `binding`. This preparation is
limited to `application.provision`, `saved_plan`, `isolated_campaign`, and an
OpenStack tuple. Other operations require their own implementation and qualification.
It compares the canonical envelope/content hashes, plan/fact expiry and the
commissioning packet's exact scope, tuple, artifacts, ownership, toolchain and
state-binding hashes. State-binding material is the five fields `backend_ref`,
`workspace`, `state_lineage`, `state_serial` and `lock_owner`. Backend references
are protected `evidence://` identities, not inline connection configuration.

The version-1 toolchain manifest contains `terraform: {version, sha256}`,
`providers: [{source, version, sha256}]`, `modules: [{id, uri, revision, sha256}]`,
`dependency_lock_sha256` and `worker_image_digest` (`sha256:<digest>`).
Use exact three-part release versions; floating ranges/tags and duplicate provider
or module entries are rejected. These are identities of the selected tools, not
a default Terraform/provider/module version or a claim of their compatibility.

The independent snapshot contains `scope`, `installed_tuple`, `artifacts`,
`ownership`, `toolchain_sha256`, `observed_at`, `observer_id`, `executor_id`,
`outstanding_operation_ids` and `terraform`. Its Terraform object carries the five
state-binding fields plus `lock_id`, positive integer `fence`, `lease_expires_at`
and boolean `held`. Observation age is bounded to five seconds. The observer must
differ from the approved executor. A changed backend/workspace/lineage/serial/owner,
missing/expired lock, changed mapping/writer, stale observation, or any unresolved
operation holds the preflight. It never proposes a blind retry or automatic cleanup.

Exit 0 means this offline comparison passed; exit 1 means invalid input; exit 2
means held. Saved-plan files are bounded to 64 MiB and JSON files to 256 KiB.
The report grants neither apply nor retry authority. The command does **not**
authenticate or fetch owner records, inspect Terraform plan semantics, verify
executable/provider/module bytes, acquire a lock, redeem a grant, execute a native
effect or confirm its outcome. Actual native adapters must obtain those records
independently, verify artifact bytes under the real state lock and current grant,
and retain independent readback. A file can change after this offline check;
its report is never a reusable execution token.

## Execute only after concrete prerequisites are supplied

Resolve ADR-014/015/016's actual tuple, interfaces and tooling with the owning
reviewers. Implement and qualify the selected native adapters and owner protocols
against those interfaces. Review G06 and current operating controls through their
existing authorities. Retrieve and compare packet contents independently before
admission; recheck current exact-scope authority immediately before each native
effect, including reservations. Keep outcomes held across response loss until an
independent observation and stale-worker exclusion settle them.

Follow all ten [Q05 cases](../../qualification/campaigns/q05-native-provisioning.md)
and the applicable [Q06 topology](../../qualification/campaigns/q06-policy-equivalence.md).
Retain original positive, negative, interruption and restore records. Successful
automation exit does not establish guest/service readiness. A failed mandatory
policy/service/data check keeps activation held. Retirement uses its own authority
and retention decision, preserves required data/keys, and releases allocations only
after independently confirmed absence. P07.06 may publish support only after the
exact native tuple and tested operations have been reviewed with those records.
