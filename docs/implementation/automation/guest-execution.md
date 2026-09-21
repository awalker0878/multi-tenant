# Reviewed guest execution

`tools/guest_run.py` and `tools/guest_apply.py` execute the selected Ubuntu profile
from a private, exactly reviewed bundle. They connect successful workload outputs
to the existing native Ansible playbook, preserving guest identity, certificate
SSH, service-file ownership and restricted bootstrap. They do not create a VM,
open platform policy, approve their own execution or activate production.

## Decisions resolved from the documentation

Use the [reference realization](reference-realization.md) and the existing
[guest](native-guests.md) and [service](guest-services.md) contracts:

| Concern | Implemented choice | Actual input still required |
| --- | --- | --- |
| Configuration owner | Ansible owns the declared Ubuntu guest files; Terraform keeps VM/network/storage ownership | Accepted image and guest-file ownership |
| Execution profile | Existing Ubuntu 24.04 chrony baseline, optionally the certificate/logging/resolver/restic service profile | Trusted image packages, initialized addresses and accepted machine/host-key identities |
| Controller | Linux/POSIX, repository-pinned ansible-core 2.19.7, Jinja2 3.1.6 and PyYAML 6.0.2; exact runtime/package bytes recorded | Recoverable, protected execution image and its external runtime reference |
| Access | Ed25519 user certificate, non-root account, pinned host key, explicit SSH executable; no ambient SSH agent/config/proxy | Current certificate/private key, image trust and scoped noninteractive sudo |
| Transfer and ordering | SSH piped transfer, one Ansible fork, serial guests, fixed playbook with no operator-supplied extra arguments | Installed SSH and guest `dd`/Python support; no TTY-dependent sudo |
| Change execution | Separate prepared `check` and `configure` bundles; exact digest approval; bounded lifetime | Current change, bootstrap, coordination and recovery handoffs |
| Interrupted work | Immutable attempt before contact, held scope after uncertainty, no automatic retry/rollback | Independently recoverable shared operator ledger and native reconciliation |

These choices remove command assembly and runtime-selection guesswork. Documents
cannot supply actual guest identities, endpoints, signatures, live convergence or
an effective native writer fence. A handoff reference identifies evidence in the
operator's trusted custody; a string does not authenticate or establish that fact.

## Prepare without guest contact

Use the exact clean published checkout. Install `requirements-dev.txt` into the
accepted Python environment; pass its absolute interpreter path and the approved
SSH executable. Preparation records their digests, interpreter version/prefix and
the installed Ansible/Jinja2/PyYAML/MarkupSafe package content digests. This detects
runtime changes; it is not a complete OS/shared-library signature or supply-chain
attestation. Qualify and protect the execution image independently.

Create an owner-only `references.json` containing exactly these keys, each with
the actual independently issued record reference:

| Key | Evidence to establish before execution |
| --- | --- |
| `target_binding_ref` | Workload output IDs, SSH addresses, machine IDs and pinned host keys refer to the same accepted guests |
| `bootstrap_ref` | Required time, resolver, administration and selected service paths are available under current native containment |
| `writer_coordination_ref` | One guest configuration owner, no conflicting image/agent/controller writer and current incident restrictions |
| `runtime_ref` | Accepted protected controller image, scoped privileges and dependency provenance |
| `recovery_ref` | Usable independent guest/OOB recovery and durable private evidence/ledger custody |

The output parent must already be private. Preparation creates a new 0700 bundle
with 0600 files outside Git and refuses overwrite or unsafe paths. Use current
private workload execution receipts where available:

```sh
python tools/guest_run.py \
  --workload-run /private/operator/workload-run \
  --access /private/operator/guest-access.json \
  --references /private/operator/references.json \
  --ssh-key /private/operator/ssh-key \
  --ssh-certificate /private/operator/ssh-key-cert.pub \
  --python /opt/hosting/venv/bin/python --ssh /usr/bin/ssh \
  --operation-id guest-check-01 --generation 1 \
  --mode check --max-seconds 600 --output /private/operator/guest-check
```

Alternatively use `--workload-outputs /private/operator/outputs.json` for exact
raw `terraform output -json` bytes under accepted external custody. It is mutually
exclusive with `--workload-run`; raw output is not a successful execution receipt.
Both paths enforce the existing complete workload/access identity contract. Receipt
handoff retains source/operation/output provenance and refuses stale, incomplete
or substituted execution artifacts. Source workloads may have been created by a
different accepted revision; the new guest bundle binds its own current revision.

The bundle contains generated inventory/known-hosts, original and rebound access,
service credential/trust snapshots, runtime metadata, references and a copy of the
required source. Service asset hashes and TLS certificate/key parsing are checked
before sealing; the sealed copies replace the original controller paths. The SSH
private key stays at its supplied private path until execution and is hash-bound.
The user certificate is bound in the bundle; the native SSH client/server still
validate the key, signature, principals, validity and image trust at connection.
Preparation does not contact a guest or issue authority.

## Review and execute the exact bundle

Review `bundle.json`, the selected mode, original/rebound access, source/runtime
and credential digests, guest-file ownership and the complete target set. `check`
predicts supported Ansible changes but is not a saved remote transaction or proof
that the later configuration will be unchanged. Service secrets and logs stay
private; never publish this bundle as a PR artifact.

The external change system supplies one owner-only JSON approval with:

| Field | Required value |
| --- | --- |
| `format` | `hosting-guest-approval/1` |
| `bundle_sha256` | SHA-256 of the exact `bundle.json` bytes returned by preparation |
| `operation_id`, `generation` | Exact bundle identity; positive integer generation |
| `valid_from`, `valid_until` | Current timezone-qualified window, at most one hour |
| `change_ref` | Exact change reference in the accepted guest access handoff |

The bundle must be at most one hour old and remain at its prepared path. The
approved runtime, clean Git revision and every source/input/service byte are
rechecked. Enough approval, guest access and enabled backup-enrollment lifetime
must remain for the entire requested timeout. Both modes contact guests and need
the explicit execution flag:

```sh
python tools/guest_apply.py --bundle /private/operator/guest-check \
  --approval /private/operator/guest-check-approval.json \
  --ledger /private/operator/guest-ledger --execute
```

Provision `guest-ledger` as owner-only durable storage beforehand. Every controller
for the same guest scope must use that same accepted ledger and coordination
mechanism. Do not select an empty ledger to bypass a held operation. POSIX flock
and directory/file fsync behavior require qualification on its actual storage;
they are not distributed native fencing.

After accepting the check results, prepare a **new** bundle with `--mode configure`
and a new operation/generation, then obtain its exact approval and execute it by
the same command. A check approval cannot become configuration authority. A later
convergence/idempotence run also needs a new reviewed bundle and operation or
generation; the same attempted identity cannot be replayed from a new directory.

The runner invokes only the copied playbook, fixed generated inventory and
approved Python/SSH binaries. It ignores ambient Ansible/Python/SSH/proxy settings,
uses a private controller home/temp directory, disables SSH connection sharing
and agent/key discovery, and restricts authentication to the supplied certificate.
SSH transfer uses the same reviewed executable with `piped`, avoiding a fallback
to independently configured SCP/SFTP clients. See the official
[Ansible SSH options](https://docs.ansible.com/projects/ansible/latest/collections/ansible/builtin/ssh_connection.html).
The existing local inventory gate runs before SSH; each guest's machine ID and
Ubuntu version are checked before guest changes. Reserved control/group names
cannot be guest member names.

## Results and interrupted execution

Before dispatch the runner writes an immutable `STARTED_OUTCOME_UNKNOWN` record,
then the scope head. Missing completion records block later work even if the
controller stopped between those two writes. Nonzero Ansible exit, timeout,
interruption, missing counters, incomplete host coverage, ignored/rescued failure
or inconsistent records leave `HOLD_RECONCILIATION_REQUIRED`. A different operation
name cannot bypass that hold. The tool supplies no ledger-release command.

On timeout/interruption the controller terminates its process group. Already
dispatched remote work can continue: preserve native containment, observe actual
guest/service state and reconcile under the accepted owner procedure before a
separately approved forward action. Never treat local process death, old output,
check mode or state-file restoration as native rollback. A forced controller stop
can leave the staged SSH key; protect the bundle and reconcile it before cleanup.

Completed results require a successful process and fresh counters for localhost
and every intended guest, with no failed/unreachable/rescued/ignored work. The
private result binds those counters by digest and records source, bundle, scope,
operation, generation and time. Outcomes are `CHECK_COMPLETED_REQUIRES_REVIEW` or
`CONFIGURED_REQUIRES_NATIVE_ACCEPTANCE`; neither proves native service acceptance
or permits production activation. The copied SSH key is removed on ordinary
completion/failure. Sealed service credentials and private evidence remain under
their retention and revocation owners.

The ledger also retains an immutable copy of the callback counters. Before any
later attempt, the runner replays those counters against the original target set
and time window, checks every receipt field against the immutable start, binds
the filename to the operation/generation, and checks the current head against the
latest complete result. Missing/orphan records, source/change/mode substitutions,
counter changes and claims of native acceptance all hold. Guest access and enabled
backup enrollment must still be current when the controller finishes.

Earlier ledgers without the recorded target set or retained counter file cannot
be silently upgraded. Preserve them for independent reconciliation with their
original bundle, callback output and native observations. Do not edit receipts,
invent missing counters, delete a hold or use a new empty ledger to resume. The
current runner supplies no migration, reconciliation-release or replay authority.

Run the [target campaign](target-qualification.md) and independently verify time,
resolver behavior, collector receipt, certificate revocation and useful-data
restore. Actual first-run/second-run convergence, privilege boundaries, remote
late effects and recovery remain [site commissioning](site-commissioning.md)
requirements. Real Ansible controller tests with a non-networking SSH fixture
prove dispatch/hold behavior; they do not configure or qualify a native guest.
