# Export accepted Terraform state for independent protection

`tools/state_export.py` reads the exact state slots from an accepted
[GitLab project handoff](state-projects.md), verifies their lineage and serial,
and creates a private export usable by the existing
[restic capture and isolated restore](restic-recovery.md) owner. It performs only
GET requests. It cannot upload state, acquire/release a lock, remove a version,
restore a backend or change infrastructure.

This is the state-copy portion of W03/W23. A local export is not an independently
protected backup, a complete GitLab service backup or an infrastructure recovery
procedure. GitLab database, object-store and encryption-secret recovery remain
separate requirements. Protect the private owner journals, approvals, plans,
source and credential recovery material through their own accepted custody.

## Inputs and source identity

Supply the original state-project request and its accepted narrow receipt.
Their complete object digests are bound by the new export request. The export
source may be a later accepted release; the original project request remains
unchanged so its native ownership marker and project ID stay stable.

A private `hosting-state-export/1` request contains exactly:

| Field | Required value |
| --- | --- |
| `format`, `enabled` | `hosting-state-export/1`; explicit boolean execution selection |
| `source_commit`, `operation_id` | Exact clean export source SHA and stable export identifier |
| `project_request_sha256`, `project_receipt_sha256` | `tools.readback_core.digest` of the original accepted project request and receipt |
| `reader_id` | Active native user ID in the accepted member list, with Developer-or-higher state-read permission |
| `states` | Complete sorted state-slot expectations described below |
| `consistency_ref` | Independent accepted writer-quiescence/application-consistency record for this capture |
| `protection_ref` | Accepted independent protection and retention destination/custodian |
| `output` | Private absolute destination outside source, under an existing private parent |

Each state expectation has exactly `state_key`, `lineage` and `minimum_serial`.
Every backend slot from the project handoff must appear once, sorted by its
compiled key. A used slot requires its independently accepted canonical UUID
lineage and nonnegative minimum serial. The minimum must reflect retained prior
state knowledge; do not lower it to accept an unexplained rollback. An explicitly
unused slot uses null for both fields and must return absence in both sweeps.
A previously used missing state is never silently reclassified as unused.

The separate `hosting-state-export-authority/1` record contains exactly `format`,
`request_sha256`, `valid_from`, `valid_until`, `change_ref`, `token_sha256` and
`ca_sha256`. It binds the full request plus exact token/CA file bytes. Absent CA
uses null and system trust. Its current timezone-aware interval lasts at most
one hour and is checked before each bounded HTTPS request. Use a read credential
whose accepted native user matches `reader_id`; the original project-bootstrap
owner token is not required.

```sh
python tools/state_export.py --request /private/state/export.json \
  --project-request /private/state/project.json \
  --project-receipt /private/state/accepted-project.receipt
python tools/state_export.py --request /private/state/export.json \
  --project-request /private/state/project.json \
  --project-receipt /private/state/accepted-project.receipt \
  --authority /private/state/export-authority.json \
  --token-file /private/state/reader-token --ca-file /private/state/ca.pem --execute
```

The default validates without contact. Explicit execution checks the current
source, reader, installed GitLab version, original native project, mandatory
private settings and complete inherited membership. Changed custody or project
restrictions hold before state collection. Only the backends compiled from the
original exact project ID/scopes can be read; the export request cannot supply
arbitrary download URLs.

## Capture and interruption

For each used slot, the tool reads latest state, requires format 4 and the
repository-pinned Terraform version, validates lineage/minimum serial, and reads
that same serial through GitLab's retained-version endpoint. Both JSON objects
must match. State files may contain credentials and private data; every stored
file is owner-only and console output contains only status and request digest.
The existing HTTPS transport refuses redirects, proxies, automatic retries and
responses larger than 4 MiB. Larger states require a separately accepted profile.

A second complete latest-state sweep must match the exported bytes, including
continued absence for explicitly unused slots. Project/custody checks repeat
around collection. These finite observations detect observed changes; they do
not create a cross-state transaction or native writer fence. The independent
consistency owner remains responsible for the accepted capture interval.
GitLab documents its [state download and retained-version interfaces](https://docs.gitlab.com/user/infrastructure/iac/terraform_state/).

Each attempt has a new numbered directory and private authority record. Failed
or interrupted captures retain any partial state files. Repeating the same
immutable request under current read authority creates a fresh read attempt,
without overwriting partial evidence. There are at most 32 attempts per export.
No failed attempt is handed to the protection owner as a completed capture.
An exact completed repeat verifies the retained full artifact map and returns
the historical receipt without network contact; its original observation time
is preserved. A fresh capture uses a new accepted operation/output.

## Protection and recovery handoff

`receipt.json` reports `STATE_EXPORT_OBSERVED_REQUIRES_PROTECTION`, complete
artifact hashes, every state lineage/serial and the exact completed `export`
directory. That directory contains only hashed-name `.tfstate` files and an
`index.json` mapping them to their accepted backend keys and native project ID.
Retained failed attempts remain outside the completed export directory.

Select this exact completed directory as the restic export `source`, bind the
export receipt digest in the accepted consistency record, capture through the
independent append-only repository authority, and retain its exact snapshot and
manifest receipts. Prove an isolated restore with the existing restore owner
and compare the recovered index/state bytes before considering the copy usable.
The state exporter leaves `independent_backup_verified` false; it cannot claim
successful protection merely because local reads completed.

Before any backend recovery, establish actual native writer exclusion, reconcile
live resources and pending operations, verify the retained lineage/serial and
accept the specific recovery plan. A restored older state file describes an
older view; it does not undo native operations. This exporter deliberately has
no state upload or rollback command. Whole-history rollback remains outside
local hash detection, so keep independent receipt custody and protection.

## Test evidence

The real TLS fixtures cover version-specific export, used/unused slots, changed
lineage, serial regression, missing state, inconsistent retained versions,
changes between sweeps, permission/identity drift, partial-read recovery and
changed completed bytes. All export requests are asserted to be GETs. These
fixtures do not qualify installed GitLab retention or independently protected
recovery; perform the actual service and data recovery exercises at commissioning.
