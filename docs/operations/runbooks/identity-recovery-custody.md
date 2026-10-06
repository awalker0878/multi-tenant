# Independent identity recovery custody and resumption

Owners: the appointed recovery owner and a different security reviewer. Execution:
SRE using a temporary migration-owner credential. Packages P02.01/P02.03/P02.04;
criteria G02.01/G02.03/G02.04; operating inputs OP03/OP05/OP06. The user authorized
implementation of this procedure on 2026-10-05. This does not appoint production
operators or authorize an actual installation restore.

## Authority and deployment

Run [custody.py](../../../scripts/recovery/custody.py) on a separately administered
custody host. Its store is outside application volumes, application backups,
deployment rollback and database-restore access. Mount only its `public/` directory
read-only into Governance. Use a directory mount that observes atomic replacement;
a bind mount of one file's old inode is insufficient. Applications must have no
custodian login, store-write capability, signing key or migration-owner credential.
Verify these denials with the actual identities and mounts before operational use.
The tool requires a private store directory, locks concurrent changes, fsyncs its
hash-linked journal and replaces descriptors atomically. Store/journal failure
prevents release. Independently retain the journal and signed records under the
appointed retention and recovery authority.

Two independently verified people have separate RSA signing keys of 3072–8192 bits,
encrypted PKCS#8 private-key files on their respective trusted workstations. Neither
private key belongs on the application or custody host. Verify public-key fingerprints
and actual operator identities through an independent channel. Distinct key bytes
and principal IDs are enforced; software cannot prove two IDs belong to different
people. Use the organization's approved key issuance, protected backup and revocation
process. Key values and passphrases never enter a repository, command argument or log.

The trust file is canonical UTF-8 JSON (sorted keys, no insignificant spaces), with
exactly `version: 1`, the real `installation_id`, integer UTC `valid_from` and
`valid_until`, and two `principals`. Each principal has `id` (its verified UUID),
`role` (`recovery_owner` or `security_reviewer`) and `public_key_pem`. Duplicate
identities, roles or keys, expired policy and writable trust files are refused.
Canonicalize protected JSON using a trusted local JSON tool; review the resulting
bytes and digest before installing it. Enrollment refuses an existing store and
cannot reset its journal or change admission state.

```sh
python scripts/recovery/custody.py enroll \
  --directory /srv/independent-identity-custody \
  --admission /restricted/current-identity-admission.json \
  --trust /restricted/verified-recovery-trust.json
```

Governance's `GOVERNANCE_IDENTITY_ADMISSION_FILE` points to the mounted
`public/identity-admission.json`. `GOVERNANCE_IDENTITY_RECOVERY_TRUST_FILE` points to
the mounted `public/trust.json`. These are recovery infrastructure references.
OIDC issuer/client/secret/claim settings remain application data configured through
Console. Provider configuration is never introduced through deployment variables.

Migration 011 reserves established binding changes and recovery receipt/release
writes to the migration owner. Runtime has read-only access to recovery records.
The narrowly scoped PostgreSQL bootstrap function can bind only a null admission
record while the bootstrap sentinel is uninitialized; it cannot rebind existing
authority. It has an explicit safe search path, no public execution grant and no
dynamic SQL. Apply all ordered migrations before the corresponding application.

## Contain and prepare

1. Record the incident, verified release/artifact, archive digest and restore point,
   authoritative current retirement/revocation/provider records, tenant-owner decisions,
   infrastructure containment and key-recovery observations. Keep the actual records
   protected; references and digests are not substitutes for examining their contents.
2. Independently block ingress/dispatch, drain both applications and stop schedulers,
   relay/consumer processes and migration jobs. Fence old native writers separately
   where relevant. This procedure governs new identity admission, not already admitted
   work or native fencing. Record the containment observations and their digest.
3. On the custody host, hold admission and generate a new unpredictable epoch **before
   restoring any database or application state**:

   ```sh
   python scripts/recovery/custody.py hold \
     --directory /srv/independent-identity-custody --case-reference REC-APPROVED-ID
   python scripts/recovery/custody.py verify --directory /srv/independent-identity-custody
   ```

   Independently observe denial at Governance and the mounted held/new descriptor.
   A failure is not permission to restore or resume. Even with a damaged journal,
   `hold` attempts the held/new descriptor first and refuses to repair history silently.
4. Restore in isolation and apply the reviewed migration set. Recover encryption
   material through its separate approved custodian. The active Console-configured
   OIDC connection must decrypt, have current verified discovery/JWKS, and match the
   independently reconciled issuer/client/administrator records. A pre-activation or
   unknown-retirement snapshot cannot use this procedure to recover local access.
5. Rotate every configured Console/service workload credential. Record the **previous**
   SHA-256 fingerprints in `previous_workloads`; record `null` only for an identity that
   was not configured. Current fingerprints are measured by the command. Unchanged
   configured credentials fail. Each current workload needs a distinct credential,
   and no previous credential may be reassigned to any workload. Disabling a workload
   is allowed. Account for old processes and peer copies before reopening.

Build a private canonical observations file with exactly these fields:

| Field | Required content |
| --- | --- |
| `case_reference` | Bounded ASCII case identifier, without narrative or secrets |
| `restore_sha256` | SHA-256 of the actual restored archive |
| `records_sha256` | Digest of the reviewed current retirement, revocation and provider reconciliation record |
| `containment_sha256` | Digest of independently observed containment/drain evidence |
| `previous_workloads` | `console`, `catalogue`, `planning`, `assurance` mapped to previous credential fingerprints or justified nulls |
| `memberships` | Up to 100 selected `{id, owner_record_sha256}` entries; use `[]` to resume identity with every tenant suspended |

Each selected membership must already be active, unexpired, tied to an enabled actor
under the current issuer, and supported by a current tenant-owner decision. Its exact
role/scope/revision, actor subject and tenant fingerprint are included in the plan.
Every selected tenant must retain an unscoped, non-expiring tenant administrator.
Selection cannot create a new member, raise a role, extend expiry or reactivate a
revoked membership. All other active memberships are revoked and their tenants
remain suspended if none were selected. Missing current facts mean leave them held.

## Two-person reconciliation

Run the following in an isolated, verified Governance installation using a temporary
`governance_migrator` database identity that can set `governance_owner`. Do not mount
that credential into the running application. Disable session recording of protected
records and keep `APP_DEBUG=false`. Output directories must be private (0700), files
private (0600), absolute, new and not symlinks. The command does not print a plan,
credential, SQL statement or provider details to the terminal.

```sh
php artisan identity:recovery prepare \
  --input=/restricted/observations.json --output=/restricted/reconcile-plan.json
```

The plan binds every owned table's count/content digest, the code and locked
dependencies, external held descriptor, current signer policy, rotated workloads,
active provider configuration/signing material, selected memberships and supporting
records. The snapshot is bounded to 100 tables and 100,000 rows per table; oversized
state remains held for a separately reviewed recovery method. Approval validity is
at most 15 minutes. Review exact bytes; an elapsed deadline requires a new plan.

Each operator receives the same protected plan and independently checks the restore,
current revocations/retirement/provider/administrator state, tenant-owner decisions,
scope, code, key recovery and containment. On each operator's own trusted workstation:

```sh
python scripts/recovery/custody.py sign \
  --trust /restricted/verified-recovery-trust.json \
  --payload /restricted/reconcile-plan.json --principal VERIFIED-OPERATOR-UUID \
  --key /restricted/operator-encrypted-key.pem --output /restricted/operator-signature.json
```

The passphrase is requested privately from the terminal. Securely return only the
detached signature; never the key or passphrase. Assemble the two approvals:

```sh
python scripts/recovery/custody.py assemble \
  --trust /restricted/verified-recovery-trust.json --payload /restricted/reconcile-plan.json \
  --signature /restricted/owner-signature.json --signature /restricted/reviewer-signature.json \
  --output /restricted/reconcile-envelope.json
php artisan identity:recovery apply \
  --input=/restricted/reconcile-envelope.json --output=/restricted/reconcile-result.json
```

Apply rechecks both current signatures, online provider/key custody, code, held
descriptor, workload rotation and the complete snapshot under exclusive owner
locks. It atomically revokes all local/federated sessions, actor delegations, delegated
grants, support appointments and pending/active approvals/support requests; consumes
OIDC flows/proofs; advances membership/tenant revisions; retires old credential
versions; and retains the immutable signed receipt and resulting snapshot digest.
Support invalidations retain their ordinary immutable audit/outbox facts. Bulk
reconciliation attribution is the signed recovery receipt, not a fabricated
federated actor or a changed published event schema. Previous histories remain intact.
An audit/receipt failure rolls back the entire reconciliation. Admission stays held.

## Separate release and fresh admission

With services still drained, prepare the post-reconciliation release plan:

```sh
php artisan identity:recovery resume-plan \
  --recovery-id=APPLIED-RECOVERY-UUID --output=/restricted/resume-plan.json
```

The two operators independently inspect the applied receipt, all resulting denials,
retained history, current owner records and unchanged custody/provider/code state.
Both sign the **new** resume plan using the same signing command with distinct output
files. Assemble its two signatures into `/restricted/resume-envelope.json`. A
reconciliation approval is never reusable as a resumption approval.

```sh
php artisan identity:recovery confirm \
  --input=/restricted/resume-envelope.json --output=/restricted/resume-confirmation.json
```

Confirmation rechecks the exact post-reconciliation state and current online trust,
then appends the immutable release authorization. It still does not open admission.
Even an accidentally active descriptor cannot admit the new binding before this
separate confirmation exists. Independently verify this record in the controlled
installation; securely convey the signed resume envelope and exact confirmation to
the custody host. A file's presence alone is not evidence it came from that database.

```sh
python scripts/recovery/custody.py resume \
  --directory /srv/independent-identity-custody \
  --envelope /restricted/resume-envelope.json --confirmation /restricted/resume-confirmation.json
python scripts/recovery/custody.py verify --directory /srv/independent-identity-custody
```

The custody tool verifies both signatures and the held generation, confirmation,
current policy and deadline. It durably records release authorization before the
last atomic admission-opening write. Bootstrap permission stays false. A crash
between those steps leaves admission held; do not replay, roll back the journal or
copy an old descriptor. Generate a new hold/epoch and re-run reconciliation.

Restart only the intended compatible processes with the rotated credentials. Require
fresh OIDC sign-in; check old local/federated/delegated/workload credentials are denied,
only selected tenant access is available, suspended tenants remain inaccessible,
current issuer failure denies new authentication, and audit/outbox delivery resumes.
Destroy the temporary migration credential and remove its mount. Retain the protected
signed plans, approvals, receipts, custody journal and actual observations independently.

On any failed observation, issue another independent hold/new epoch, block ingress,
drain work and investigate. Never use an old active descriptor to make a restore
appear current. A subsequent database restore must start with a new custody hold;
restoring a confirmed receipt does not grant rights under a newer epoch.

## Lost keys, lost bootstrap and limits

If a custodian key is missing, revoked or expired, remain held. Recover/replace it
through the separately authorized enterprise key-custody process and verify the new
public identity out of band. Changes to the mounted trust file invalidate outstanding
approvals. No application login can appoint a recovery signer or override this hold.

Lost pre-activation bootstrap credentials are not reset by this mechanism. An older
unretired snapshot is rejected even with two recovery signatures. Preserve the
installation and use the accountable clean-installation/data-recovery decision or a
separately reviewed recovery design; do not revive a retired local administrator.

This mechanism depends on actual independent host, mount, backup, key and change
custody. A privileged party that can co-restore the database and the entire old
active custody/trust environment can defeat a filesystem generation fence. The tool
does not claim a remote consensus service, hardware anti-rollback counter, production
KMS deployment, native fencing, HA or accepted RTO/RPO. Its disposable qualification
proves the mechanism; actual OP03/OP05/OP06 assignments and isolation observations
remain required before production use and G02 receiving.
