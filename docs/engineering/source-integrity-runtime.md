# Package-owned source integrity verification

Reviewed 2 October 2026. This B05 continuation moves the active release/source byte
verifier into `provisioner.execution.source_integrity` and removes the former tools
module without an alias. It is a consistency gate, not a signature, architecture
approval, native qualification or deployment authorization.

## Current checkout contract

The caller supplies an explicit current checkout, or the source-development runtime
uses its package-selected source root. The verifier resolves exactly one repository
root and one `HEAD^{commit}`, accepts only the repository's current 40-hex SHA-1 object
format, enumerates that commit's full tree and compares every regular tracked blob to
the worktree using Git blob hashing. Missing, changed, linked or unsupported tracked
objects hold. Untracked source files, staged differences and HEAD movement during the
check also hold. Ignored build output remains outside the committed-source assertion.

Git execution removes ambient `GIT_*` overrides, disables system/global configuration,
replacement objects, fsmonitor and untracked-cache refresh, forbids terminal prompts
and lazy fetching, and uses finite command deadlines. This prevents ordinary caller
environment settings from relabelling another tree as the selected checkout. It is not
a lock against a privileged concurrent writer or a cryptographic signature over Git
metadata. Trusted repository/artifact custody remains external.

Tracked file reads use no-follow regular-file descriptors with finite byte bounds and
compare descriptor/path identity and timestamps around streaming. Git metadata, file
count and each file size are bounded. Unsupported object modes/types and invalid UTF-8
paths fail closed instead of being ignored.

## Explicit export contract

A source export without Git metadata is verified only when the operator supplies a
separate manifest containing exactly `file_sha256`. Manifest JSON is bounded and rejects
duplicate properties, non-finite numbers, unsafe paths and non-lowercase SHA-256. Every
listed path must be a contained unlinked regular file whose bytes match. The manifest
does not claim completeness beyond its explicit list, authenticate its issuer or fall
back to any historical repository release manifest.

Installed distributions have `SOURCE_ROOT = None`; invoking checkout verification there
without an explicit root returns `BLOCKED_NO_CURRENT_CHECKOUT`. This prevents an
adjacent working directory from silently becoming the package's source authority.

## Ownership and verification

All live Python callers, CI source-integrity invocation and repository handoff helpers
use the package owner. `tools/check_release.py` is a retired path; preserved old release
manifests/audit transcripts may still name it as historical evidence and are not edited.
Installed-package tests require the package owner and absence of the retired module.
Disposable Git tests cover dirty/staged/untracked/missing files, HEAD movement, ambient
Git overrides/replacements/fsmonitor, symlinks, bounded export manifests and explicit
CLI root selection.

This closes one B05 runtime owner only. Reservation/IPAM/DNS preflight and additional
execution/evidence owners, retained-state conversion, signed artifact custody and native
operating acceptance remain separate plan obligations.
