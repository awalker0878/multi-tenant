# Identity, certificate and cryptographic trust assurance

**Purpose:** close the identity/PKI/KMS portion of I07 without turning this repository into an identity provider, PAM service, CA, KMS/HSM, secret store or recovery authority.

Local mutual-TLS and credential-withdrawal fixtures are useful protocol evidence, but they do not establish enterprise identity scoping, privileged-access controls, certificate lifecycle, key-authority separation, KMS outage behavior or independent trust recovery on the selected service implementation.

## Source obligations

- IAM-001 requires separately scoped human, workload and automation authorization with no tenant-to-provider authority inheritance.
- IAM-002 requires hardened privileged access, strong authentication, least privilege, time-bound delegation and tested/revoked emergency and supplier access.
- IAM-003 requires credential/session revocation to be observed at the consuming service, including cached tokens/delegated grants.
- CRY-001 requires versioned cryptographic profiles, endpoint identity validation, module/operating-environment evidence and explicit exceptions.
- CRY-002 requires key use, administration, recovery and destruction to have separated authority and dependency records; destruction cannot invalidate required retained-data recovery without approved disposition.
- CRY-003 requires tested KMS/trust outage behavior with no plaintext fallback plus maintained cryptographic inventory, certificate rotation and algorithm-transition plans.
- SVC §3 requires recovery trust material to survive the platform/control dependency it is intended to recover.

## Active assurance index

The active index is `sources/capabilities/identity_crypto_assurance_index.json` and is intentionally empty.

A future record binds one trust scope to:

- site and service class;
- trust profile and key profile;
- accountable owner;
- review cadence.

## Identity and privileged-access evidence

Current identity evidence covers human, workload and automation scopes separately, provider-authority separation, hardened privileged path, strong authentication, time-bound delegation, emergency access, supplier access and revocation behavior including cached-token tests.

Network reachability or a successful login is not authorization evidence.

## Certificate and protocol trust evidence

Current certificate evidence covers issuer, relying-party trust, endpoint identity validation, issuance scope, renewal, revocation, TLS profile and cryptographic module/operating-environment evidence.

A current algorithm name or TLS handshake alone does not prove correct endpoint validation, certificate lifecycle or validated product mode.

## Key authority and retained-data dependency

Key use, administration, recovery and destruction authorities must be four explicit separated records.

The key block also requires:

- retained-data/copy dependency reference;
- destruction-disposition decision;
- custody record;
- key-version inventory;
- rotation evidence.

This prevents key destruction from being treated as an isolated technical action when retained copies still require recovery.

## Outage and independent recovery

Current outage/recovery evidence requires:

- KMS outage test;
- explicit no-plaintext-fallback evidence;
- trust-service outage test;
- independent recovery path;
- emergency identity;
- recovery audit evidence.

Independent recovery means a surviving, accountable path—not unrestricted duplicate administration.

## Cryptographic agility

The record requires current cryptographic inventory, certificate-rotation plan, algorithm-transition plan and exception register.

## States

Supported states are:

- `CURRENT_QUALIFIED` — trust, certificate, key, outage/recovery and agility evidence are current with no OPEN gaps;
- `REVIEW_DUE` — scope or gap review expired;
- `TRUST_EVIDENCE_DUE` — identity/certificate/key/agility evidence is stale;
- `OUTAGE_TEST_DUE` — trust evidence remains current but outage/recovery evidence is stale;
- `GAPS_OPEN` — current evidence exists with unresolved trust gaps;
- `UNCERTAIN` — authoritative trust state requires reconciliation.

## Readiness preflight

`scripts/check_identity_crypto_readiness.py` evaluates one exact site/service/trust/key-profile scope.

A successful result is `IDENTITY_CRYPTO_CURRENT_NO_TRUST_MUTATION_AUTHORIZED`.

It does **not** authorize credential issuance/revocation, certificate enrollment, key rotation/destruction, privileged-access change, recovery execution, infrastructure apply or production activation.

Current repository state remains held because no target identity/PKI/KMS implementation has supplied current evidence:

```sh
python scripts/check_identity_crypto_readiness.py examples/identity_crypto_readiness_intent.json.example --as-of 2026-09-18T23:00:00Z --expected-status HOLD_NO_CURRENT_IDENTITY_CRYPTO_ASSURANCE
```

Storage ownership/copy-lineage/performance/sanitization obligations remain a separate I07 residual and are not closed by this trust gate.

[SVC §3 — Identity, certificates, keys and independent recovery](../architecture/shared-services/3-identity-certificates-keys-and-independent-recovery.md) · [CRY allocation](../implementation/allocation/cry.md) · [IAM requirements](../assurance/requirements.md#IAM-001)
