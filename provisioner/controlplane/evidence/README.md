# Evidence checkpoint slice (B13, partial)

This slice stores JSON receipts and manifests of at most 1 MiB by SHA-256
digest. PostgreSQL records tenant-scoped immutable evidence entries and a
per-tenant hash chain. A separate checkpoint store records a signed high-water
hash. Reads verify the signing identity, checkpoint scope, all chain links and
artifact bytes. A restored database older than its independent checkpoint is
held. The signing key never belongs in PostgreSQL or the artifact directory.

The caller obtains a trusted `TenantContext` from the authenticated server
principal and separately enforces operation and read policy. Do not expose
`initialize`, `append`, file paths or raw database connections to HTTP clients.
`initialize` is a one-time operator-controlled genesis action. If the external
checkpoint is later missing or invalid, reads and writes fail closed. A failed
checkpoint publish after a committed entry leaves an unanchored suffix; retry
the exact event key after restoring checkpoint service, or run the explicit
`checkpoint` operation under operator control. Never silently reset it.

`FileArtifactStore` and `FileCheckpointStore` are atomic create-only local
adapters. They demonstrate restart durability, not storage immutability, a
separate security domain, encryption or disaster recovery. A production
deployment needs object retention/versioning and independently administered
high-water storage, backup/restore tests, a real key-management signer and a
configured verifier trust list with rotation/revocation. The signing and
verification protocols fail closed when a provider is absent. The tests use
ephemeral Ed25519 keys; there is no embedded production key or HSM claim.

The JSON input guard refuses credential-shaped field names, URLs and common
authorization strings. It cannot prove arbitrary free text is secret-free;
future producer-specific evidence schemas and log/history redaction are needed
before the B13 secret-leakage acceptance gate is met. Workload disk bytes and
large exports belong to scoped data movers, not this 1 MiB receipt store.

The signed chain currently covers `evidence_entries`, not the pre-existing
`audit_events` table. Anchoring the latter needs a commit-order-safe audit
stream or privileged serialization of concurrent audit inserts. Giving an
application checkpoint role broad UPDATE on append-only audit rows solely to
obtain a table lock would weaken the existing permission boundary. B13's
whole-audit-log checkpoint and independent storage qualification remain open.

Runtime SQL grants: `SELECT, INSERT, UPDATE` on `evidence_streams`; `SELECT,
INSERT` on `evidence_entries`; schema `USAGE`. The migration role owns DDL,
the runtime role is `NOSUPERUSER NOBYPASSRLS`, and the signer/checkpoint
custodian must have a separate identity. Do not grant UPDATE or DELETE on
`evidence_entries`. The append-only trigger also prevents accidental mutation.
