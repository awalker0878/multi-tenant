# Authenticated retained-state import and owner handover

The installed `provisioner.controlplane.conversion.runtime` command imports one
explicit workload scope into the existing PostgreSQL canonical record, native
ownership and audit owners. Migration `0031_retained_state_handover.sql` retains
immutable batch, file, native binding, original start and independent proof
receipts under forced tenant RLS. Import leaves the service observation-only.
It does not stop old writers, issue credentials, start Temporal workflows or
call a native platform. The [offline rehearsal](retained-state-conversion-rehearsal.md)
remains a separate unauthenticated preparation tool.

## Supported source boundary

The exact outer `hosting-retained-state-import/1` manifest contains `inventory`
(the complete existing `hosting-retained-state-rehearsal/1` inventory), explicit
`workloadHistoryFiles`, `sourceDatabaseBoundary` and `sourceWorkflowBoundary`.
One current canonical `hosting.platform/v1` Workload and its contiguous original
revisions 1 through N are required. The current file must be revision N; no
revision is reset or omitted. Membership/cutover transitions needing original
verified authority are held until their specific original authority mapping is
implemented. The concrete Terraform output mapping remains the selected
OpenStack workloads contract; unsupported profiles stay held.

Each boundary contains exactly `format`, `mode`, `recordCount`, `snapshotDigest`,
`auditSequence`, `auditHeadHash`, `evidenceSequence` and `evidenceHeadHash`.
Formats are `hosting-retained-postgres-boundary/1` and
`hosting-retained-workflow-boundary/1`. `NOT_DEPLOYED` requires explicitly signed
zero counts/sequences and zero digests. It is never a default for missing data.
`CANONICAL_FILES` for PostgreSQL requires the full history count and the SHA256
of the canonical JSON map from sorted history/current filenames to their exact
original SHA256 values. Original database audit/evidence watermarks must be
attested independently. This bounded importer does not synthesize arbitrary
database rows from a database dump. Existing Temporal histories require their
original export/import owner; this profile accepts only an independently
attested `NOT_DEPLOYED` workflow source. Missing deployed history is a hold.

All input files, directories and output documents must be owner-private. The
complete sealed source inventory is rechecked around import. Every original
byte, including an empty writer lock or credential-bearing Terraform file, is
retained in a separately administered, KMS encrypted COMPLIANCE Object Lock
bucket. These raw bytes never enter the sanitized evidence artifact bucket.
The original byte digest is the content identity; the storage wrapper records
its exact byte extent and supports empty files. Every retained version must
match and remain in COMPLIANCE retention; delete markers and custody loss hold.

## Independent proof and database roles

Administrators independently enroll current Vault Transit verification keys in
`retained_conversion_keys` for the exact organization, tenant, WSD, workload and
full scope digest. Each purpose uses a different physical Transit key and
subject: `IMPORT`, `CUSTODY`, `NATIVE`, `EXCLUSION`, `OWNER`, `SECURITY`. Two key
labels cannot alias one Transit key. Key enrollment records the separate
non-bypass database `verifier_role`; runtime cannot enroll keys or certify its
own proof. Append-only revocations serialize with write admission checks.

Each retained `RECOVERY_DECISION` evidence artifact is an envelope with exactly
`payload`, `statement`, `keyId` and `signature`. The payload is
`hosting-retained-conversion-proof/1` and contains `purpose`, `batchId`,
`manifestDigest`, `scopeDigest`, `statementDigest`, `subjectId`, `observedAt` and
`freshUntil`. Digests bind exact outer-manifest bytes, full canonical scope JSON
and statement JSON respectively. Scope, statement and file-map digest bytes use
the existing `run_files.encoded` owner: sorted keys, two-space JSON indentation,
ASCII escapes, no non-finite numbers and one final newline. The proposal supplies
the exact scope digest. `signature` is base64 of the raw versioned
Vault signature bytes returned by the existing Transit signing owner, covering
the existing evidence owner's canonical payload JSON. Proof observations must
be current at the database clock and expire within five minutes. Files and
local signer names cannot establish trust. Each use verifies the retained
evidence/checkpoint chain, original signed envelope, actual Vault signature,
current enrolled scope/key and independent SQL verifier receipt.

| Database identity | Narrow conversion privileges |
| --- | --- |
| Runtime importer | SELECT all nine conversion tables; INSERT only batches, files, bindings and recovery. Existing canonical/native/audit owners retain their current privileges. EXECUTE state, write-admission and accept-handover functions. |
| Site worker | EXECUTE `retained_conversion_write_is_admitted(text,text,text,text)`; existing started-job enterprise visibility is unchanged. |
| Independent proof verifier | SELECT keys, key revocations, proofs and existing evidence entries; INSERT proofs. No batch or handover INSERT. |
| Independent key commissioner | SELECT/INSERT keys and key revocations. No runtime key commission authority. |

The public state function is `retained_conversion_state(text,text,text)`.
`accept_retained_conversion_handover` has ten text arguments. Runtime has no
INSERT privilege on keys, proofs, handovers or resolutions. No conversion table
grants go to PUBLIC. All enrolled identities must be NOSUPERUSER/NOBYPASSRLS.
The accepted transaction alone writes handover/resolution rows and advances the
existing native owner epoch. Direct idle epoch advances remain denied.

## Operator sequence

Configure the existing independent evidence runtime with pinned verify-full
PostgreSQL TLS, pinned HTTPS Object Lock and Vault trust, protected credential
files and a current separate checkpoint runner. Add required
`HOSTING_CONVERSION_ORIGINAL_BUCKET`, `HOSTING_CONVERSION_ORIGINAL_PREFIX` and
`HOSTING_CONVERSION_ORIGINAL_KMS_KEY_ID`. The raw original bucket must differ
from both evidence and checkpoint buckets and its access policy must restrict
the credential-bearing originals. Only the proof intake process receives
`HOSTING_CONVERSION_VERIFIER_DSN_FILE`, a protected URI DSN for the enrolled
separate verifier. This command has verification credentials; it never enrolls
checkpoints, keys or operating instances.

1. Inventory every old writer, queued/accepted request and original native task.
   Stop and exclude the actual submission paths and old credentials outside this
   command. Retain the complete source inventory, explicit source boundaries
   and immutable original manifest. Observe the new service without write
   authority. Missing native IDs, freeze or source records remains held.
2. Run `python -m provisioner.controlplane.conversion.runtime propose --manifest
   <private-manifest> --source-root <private-originals> --output
   <private-proposal>`. The proposal contains exact import/custody commitments;
   it does not create a signature, native observation or acceptance.
3. The four separate current authorities retain signed `IMPORT`, `CUSTODY`,
   `NATIVE` and `EXCLUSION` evidence through the existing evidence owner.
   Native proof binds every original native identity/lifecycle stage and every
   original operation/generation, with explicit task identity/quiescence and
   disposition. Unknown starts may be imported as held history. Exclusion proof
   must identify all actual old writers and exclude queued submissions.
4. Under the separately enrolled proof verifier, run `intake --manifest
   <private-manifest> --purpose <purpose> --event-key <retained-event>` for each
   proof. Then runtime runs `import --manifest <private-manifest> --source-root
   <private-originals> --proof-events <private-four-event-map>`. Import archives
   exact bytes and inserts canonical history, native IDs at the original idle
   epoch, file/count facts and original recovery facts in one SQL transaction.
   An exact repeat is idempotent. Changed batch bytes conflict.
5. Have the independent checkpoint runner anchor the newly appended audit
   suffix. Run `inspect --organization-id <org> --tenant-id <tenant> --batch-id
   <batch> --output <private-inspection>`. Its reconciliation digest is the
   server's exact JSONB state digest, including current canonical history,
   native epochs/workers and B09 original outbox workflow start/run/high-water
   facts. Do not recompute it with a different JSON serialization.
6. Resolve every old native start through fresh independent readback and old
   writer/task exclusion. Five separate current `NATIVE`, `EXCLUSION`, `OWNER`,
   `SECURITY` and `CUSTODY` proofs must accept that same inspection. Native and
   exclusion proofs bind its reconciliation digest and exact retained source
   inventories. Every original task must be quiescent with known `NO_EFFECT`
   or `EFFECT_PRESENT`; absence or timeout cannot authorize replay. Owner and
   security statements must match exactly and include the declared original
   epoch to original+1 for each binding and a bounded `writeAdmissionUntil`.
   Old writer subjects cannot accept their own exclusion/handover.
7. Intake those five retained events independently. Run `handover
   --organization-id <org> --tenant-id <tenant> --batch-id <batch> --proof-events
   <private-five-event-map>`. SQL rechecks current keys, complete counts/history,
   the inspection digest, original task dispositions, inactive exact native
   owners and canonical recovery/containment before its atomic epoch advance.
   Only this current exact scope becomes write-admitted. A repeated exact
   receipt advances nothing; a different first handover conflicts.

Each subsequent existing native owner acquisition/renewal, original intent
registration/preparation/claim and mutating worker grant use requires current
conversion admission in addition to its normal plan, approval, worker, grant,
lease, native recovery and operating-instance authority. Read-only discovery
keeps its existing path. Key revocation, key expiry or acceptance deadline closes
the converted scope. Historical UNKNOWN start rows and original bytes never
change: an accepted known disposition is a separate immutable no-replay row.

This owner implements one bounded first handover, with a maximum one-hour
acceptance and enrolled key expiry bound. It does not silently renew that
acceptance or advance a second conversion epoch. A further reviewed renewal
owner, deployed Temporal/state exports, extra retained record profiles, actual
old-writer stops, external native readbacks and service handover evidence remain
separate required work where those deployment inputs exist. Operating instance
restore/HA controls remain independently mandatory. Import or acceptance never
qualifies a native migration, guest boot or release campaign.

## Validation boundary

Run `python -m unittest discover -s tests/provisioning/conversion` and
`python -m unittest tests.provisioning.reconciliation.test_job_scope_storage`.
The local cases use authentic canonical records and real original Terraform
writer formats, real independent Ed25519 signatures behind a synthetic Transit
HTTPS port and a synthetic Object Lock transport. The opt-in isolated
PostgreSQL cases execute the actual migrations, non-bypass runtime/verifier/
commissioner permissions, forced RLS, original import and atomic epoch guard;
their external native/custody services remain synthetic. Missing PostgreSQL
DSNs produce explicit skips. These tests prove implementation contracts and
do not provide authentic retained deployment, fencing or migration evidence.
