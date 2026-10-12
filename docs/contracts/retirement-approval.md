# Canonical contract retirement and installed-copy removal

This repository deliberately ships only active contract bundles. **Small checkout
size does not waive independently reviewed external-consumer obligations.**
Existing historical removals remain visible through Git and the frozen list in
`architecture/retirement-unverified-baseline.txt`.

## Canonical retirement: two separate reviewed changes

1. **Assessment / pre-approval:** inventory all supported and external clients,
   installed/packaged copies, generated clients, contractual support periods,
   deployment versions, open-source integrations, and documented public APIs.
   Produce durable HTTPS evidence for the consumer inventory and compatibility
   disposition. Independently review this assessment in a GitHub pull request.
   The review PR description must link both evidence documents. A reviewer other
   than the PR author must approve it and the PR must be merged.
2. Add an approved entry to `architecture/retirement-clearances.json` in that
   review PR. Record `status=approved`, `decision=retire`, the owning team,
   independent reviewer GitHub login, actual review submission timestamp, the
   merged review PR URL, SHA-256 of the exact canonical bytes, assessed consumers,
   both evidence URLs and compatibility commitments (`none` or `satisfied`).
   **Do not delete the canonical file in this change.**
3. **Removal / subsequent PR:** delete the superseded canonical file and update
   both `architecture/contract-consumers.json` and
   `architecture/retired-contract-releases.json`, including the independently
   established consumer status and the same external evidence and commitments.
4. P01 and Contract Integrity compare the actual Git review-base canonical tree
   with the working tree, not merely the editable active registry. They reject
   undeclared deletions, in-place mutation, unapproved retirement, same-change
   clearance forgery or a missing review-base approval.
5. For any **new** retirement, the GitHub API verifies that the prior review PR
   was merged, its merge commit is in the review base, and the recorded reviewer
   gave a current APPROVED review before the merge. The PR body must contain both
   evidence references. CI needs read-only pull-request access. A local removal
   run requires `GITHUB_TOKEN` and fails closed without it.

This is a technical proof of an independently *reviewed* decision, not a claim
that code can discover every unknown external consumer. The accountable owner
and independent reviewer must verify the truth of submitted evidence.

## Historical debt

The 53 previously removed releases are pinned to a frozen Git-blob digest and
remain explicitly `not-independently-verified`. This pre-enforcement exception
is not permission to add more unreviewed removals or to mark these records
cleared without actual assessment. Reconcile each historical version with the
same inventory, contractual-disposition and independent review process, and
retain the actual decision evidence. Do not fabricate clearances or automatically
restore files without an actual external compatibility requirement.

## Removing installed consumer copies

Installed copy removal is **separate** from canonical retirement. The active
copy inventory is in `architecture/installed-contract-usage.json` and must
match every installed copy in the registry. A copy may be removed only when:

- Its production loader no longer imports it, including Planning's typed
  dynamic owner-operation mapping.
- All source assembly manifests and generated clients target the replacement.
- The Dockerfile or Python wheel packaging and every relevant CI check targets
  the replacement; no active deployment requires the old path.
- The canonical producer/consumer validation still passes on actual responses.
- The ledger, deployed copy and registry declarations are updated together.

`scripts/contracts/installed_usage.py` verifies the current ledger against
loaders, wheel/image packaging, known generator scripts, source manifests, CI
invocation and canonical byte parity. Runtime discovery remains an independent
backstop and rejects unregistered shipped artifacts.

## Gates

```sh
python scripts/contracts/retirement_integrity.py
python scripts/contracts/check.py
python scripts/p01/contracts/compatibility.py --base "$(git merge-base origin/main HEAD)"
python scripts/p01/contracts/test_compatibility.py
```

The Contract Integrity workflow and P01 workflow execute the Git-baseline
gate with full Git history and the read-only GitHub token.
