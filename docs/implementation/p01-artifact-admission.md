# P01 artifact trust and repository admission

P01.04; R02/R31/R35; platform/security reviewers. The current increment implements
receiving-side validation and conservative review predicates. Actual repository
settings and operated registry/signer/receiver identities remain separate inputs.

## Implemented boundaries

- The versioned consumer registry describes implemented Catalogue-to-Planning facts
  and Inventory/Lifecycle workers. Build selection unions base and head owners and
  dependency edges; deleting an edge cannot silently drop its earlier consumer.
  Unknown ownership selects broadly and blocks admission.
- A PR admission workflow checks out only the exact target base. It fetches head/merge
  objects as data and runs no proposed source, build, dependency installer or action.
  Read-only GitHub access checks current account IDs/permissions, exact-head review,
  resolved threads, distinct critical reviewers and the check application's exact
  tested merge revision/parents. The checked-out base owns role/exception policy.
- Role mappings start explicitly UNCONFIGURED. No CODEOWNERS account, review or
  approval is invented. The policy denies admission until mappings are verified.
  The first real draft PR did not trigger this new workflow: GitHub evaluates
  pull_request_target from the repository default branch, where this hook has not
  been installed. A separate read-only push probe exercises the exact target-base
  evaluator against that disposable PR; it is not an automatic admission hook.
  Installation must also publish its decision against the actual PR revision
  through the approved independent reporting identity before protection is enabled.
  An administrator must rerun admission after constituent checks/reviews finish;
  its initial event execution may correctly hold an incomplete PR. Protection
  settings must require its actual reporting context before it enforces merges.
- Exceptions require exact files/rules, a real allowed reviewer, source binding,
  compensating check/removal task and a bounded UTC expiry. Wildcards and attempts
  to exempt native fencing are denied. Candidate-added exceptions require actual security approval and cannot authorize
  their own use; only previously admitted base records apply to changed files.
  Expired unrelated records do not prevent a reviewed cleanup of the policy. No exceptions are currently active.
- The artifact verifier binds OCI manifest/config/uncompressed-layer digests,
  independently supplied source/component/key/builder anchors, SBOMs, signed
  provenance and fresh scans. A bundled key cannot authorize itself. Missing,
  altered, stale, unsigned, wrong-source, revoked-key or security-finding cases fail.

## Signing/scanning development selection

Cosign 3.1.3 and Trivy 0.75.0 are exact development tool candidates. Their official
release asset SHA-256 values are locked in `release/artifact-tools.lock.json`.
Downloads verify those bytes before execution; no mutable installer is run. This
is checksum-pinned tool selection, not independent qualification of the tool supply
chain or adoption of an operated trust service.

The signing fixture generates a fresh private key outside the bundle and destroys
it afterwards. Its explicit signing configuration has no CA, OIDC, timestamp or
transparency-log destination; network proxies deny accidental signing traffic.
The verifier accepts that no-log mode only for `p01-development`. It does not satisfy
operated identity, transparency, revocation freshness, key recovery or custody.
No repository source or candidate manifest is published to a public signing log.

Local verification passes 16 review/impact/exception tests, seven exact-check-source
tests, four exclusion tests, two evidence-redaction tests and 12 actual Cosign bundle tests, including positive transfer and explicit failure boundaries.
Fixture account IDs, scan records and images are synthetic and confer no real role,
image-security result or product promotion. The image workflow now scans each existing built image and its exact owned source,
including development/build dependencies, and retains CycloneDX SBOMs, redacted
findings, advisory database identity, source/lock hashes, provenance, signature and
receiving-anchor observations. HIGH/CRITICAL/UNKNOWN vulnerabilities, any secret,
incomplete scans or stale evidence hold the candidate and fail the image aggregate.
A successful control exercise is recorded separately from candidate admission.
Raw scanner output and private keys remain temporary. Only a clean development
candidate is copied to a fresh destination and reverified; the image is never
rebuilt during transfer. Real hosted results remain pending execution.

The first hosted scan attempt (source `2e1be599cba89275c92396066f091779cd912539`,
run 37264412362) held all nine candidates because the image scanner does not accept
the filesystem-only development-dependency flag. No image-security pass was
reported. The correction applies that flag only to source scans and disables
implicit local scanner/ignore configuration; image configuration secrets are
scanned explicitly. The failed observation remains part of the qualification trail.

## Primary interfaces

- [Cosign blob signing](https://docs.sigstore.dev/cosign/signing/signing_with_blobs/)
  and [verification](https://docs.sigstore.dev/cosign/verifying/verify/).
- [Trivy image scanning](https://trivy.dev/latest/docs/target/container_image/)
  and [CycloneDX generation](https://trivy.dev/latest/docs/supply-chain/sbom/).
- [OCI image layout](https://github.com/opencontainers/image-spec/blob/v1.1.1/image-layout.md)
  and [manifest](https://github.com/opencontainers/image-spec/blob/v1.1.1/manifest.md).
- [GitHub workflow events](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows).

This implementation supplies control mechanisms and measured fixture denials. It
is not G01 acceptance, enforced branch protection, independent SLSA-level assurance,
production promotion, whole-release qualification or an operated trust decision.

The receiving inputs and concrete settings candidate are in [the operating-input
record](p01-operating-inputs.md). Analyzer configuration changes require platform
and security roles; newly added inline suppressions require a prior exact-file,
exact-source exception with a bounded expiry and required compensating check.
Current exceptions remain empty.
