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
Raw scanner output and private keys remain temporary. A clean development candidate is copied to a fresh destination and reverified.
A held image may be copied only to the campaign quarantine: every byte must match
and the receiving verifier must still deny it. The image is never rebuilt during
transfer and a quarantine copy confers no deployment eligibility. The real hosted
results are recorded below; all candidates remain held.

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

The [retained-byte correction](p01-evidence-retention.md) restores original build
log bytes and adds a continuous digest check. Original report hashes remain intact.

The receiving inputs and concrete settings candidate are in [the operating-input
record](p01-operating-inputs.md). Analyzer configuration changes require platform
and security roles; newly added inline suppressions require a prior exact-file,
exact-source exception with a bounded expiry and required compensating check.
Current exceptions remain empty.

## Initial real-image findings and correction

Run 37264699751 completed all nine real-image control campaigns at source
`4d4b12d1e1b4e5db880d5b0722b7ad6715160d69`. Each candidate was correctly held.
The nine exact owned-source scans, including development dependencies, had zero
blocking findings. The four PHP images had 259 blocking package/advisory matches
each (215 distinct advisory IDs); the five Python images had 65 each (25 distinct
IDs). These are scanner observations requiring triage, not claims of exploitable
product behavior. No scanner ignore file or risk waiver is applied.

Two findings have published fixes: libpcre2-8-0 `10.42-1+deb12u2` and tzdata
`2026c-0+deb12u1`. Both packages are available in the already selected signed
20261004 Debian snapshot. All nine runtime builds now request those exact versions.
The PHP runtime additionally removes unused linux-libc-dev headers during existing
build-tool cleanup. Corrected run 37265822363 at source
`41bbcaec3be5ec0f2abdd534bab2041e46a74e90` rebuilt and probed all nine images,
verified the exact two installed package versions, and rescanned their real bytes.
All nine owned-source scans have zero blocking findings. The four PHP candidates
each retain 80 blocking package/advisory matches (36 distinct advisory IDs); the
five Python candidates each retain 63 matches (23 distinct IDs). None of those
remaining matches has a scanner-provided fixed version. The observations do not
establish exploitability or authorize a waiver. Every image stays HELD.

The corrected campaign measured 81 expected denials, nine development signatures
and nine unchanged-byte transfers into quarantine. Retrieval reverified all nine
retained manifest signatures, 198 build-log hashes and 225 unique source bindings.
Its workflow intentionally failed image admission. A passed denial control is
recorded separately from that failed candidate decision.

## Complete candidate evidence set

[The generated manifest](../../release/p01-candidate-set.json) composes all seven
applications and both selected workers from the corrected run. It binds each
source path, revision, lock, image/config digest, build report, SBOM, provenance,
development signature and negative-case report. The generator rejects missing
components, a changed registry, mixed sources, altered retained bytes and a claim
that a held candidate was admitted. It is a historical development evidence set,
not a deployable product release; full image layers are not retained here.

Regenerate with `python3 scripts/p01/artifacts/release_set.py --run-path verification/p01/artifact-trust/run-37265822363 --output release/p01-candidate-set.json`.
Normal CI uses `--check` to reject stale generated content. Historical freshness is
evaluated at the original observation time; later promotion needs new scans and
independent full-artifact/trust verification.

Receiving-side verification also rejects a correctly signed empty scan inventory,
missing advisory-database digest, mislabeled scan scope and empty source SBOM.
These controls are exercised with real Cosign signatures, without weakening the
existing HIGH/CRITICAL/UNKNOWN or secret finding holds.

The policy workflow now separately scans exact tracked repository content,
including policy, deployment, tests, documentation and retained evidence. It
stages no untracked local caches and adds no source-tree exclusion. A generated
non-credential validates the detector in a separate temporary directory. Only
rule/location metadata and source hashes leave temporary storage; matched bytes
and source snippets are discarded. The scanner binary is verified against the
recorded extraction of the existing checksum-locked archive. This closes the
coverage gap between component-only scans and repository content. Trivy remains
a heuristic text detector; success does not prove that no secret exists or scan
Git history. See [the scanner documentation](https://trivy.dev/latest/docs/scanner/secret/).

EV-P01-023 retains hosted run 37269433140 at source
`48a998c8b4517f5d27933973d9d4b04677b48e49`: all 59 policy-control tests passed,
including 14 real-signature cases, and the positive-controlled repository scan
reported zero secrets across 9,766 tracked files. Retrieval independently matched
every source hash to the immutable Git tree and retained the original redacted
scan report in its hash-verified ZIP. New image run 37269433149 at the same source
again passed each of nine control campaigns while holding all nine candidates;
the observed job summaries retain those distinct outcomes.
