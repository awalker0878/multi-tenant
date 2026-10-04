# Package-owned capacity and allocation planning owners

Reviewed 2 October 2026. This B05 continuation removes the remaining allocation-chain runtime imports from top-level `scripts` and places them under `provisioner.allocations`. It changes code ownership and input hardening only; it does not create reservations, allocate addresses, write DNS, contact a native platform or authorize production.

## Installed owners

The installed package now owns the site/service capacity evidence reader, site eligibility evaluator, reservation preflight, IPAM preflight and DNS preflight together with the already package-owned reservation, IPAM and DNS exported-evidence readers. `provisioner.repository` consumes those package owners directly. No `provisioner` module imports `scripts` or `tools` after this change. The former five script paths are retired without forwarding modules.

The existing record and intent formats, status vocabulary, canonical digest rules, exact operation identities and owner boundaries are unchanged. Reservation remains external authority; IPAM values remain external and absent from repository evidence; DNS names and A/AAAA/PTR values remain external. Preflights return readiness/hold information only and keep every mutation/apply/activation authority flag false.

## Evidence input boundaries

Reservation, IPAM and DNS exported-evidence readers use packaged resource defaults rather than the process working directory. IPAM and DNS indexes are bounded regular files, reject links/junctions, duplicate JSON properties, non-finite values, excessive input and observed replacement/change during reads, and require canonical contained source references. Missing packaged evidence does not fall back to a similarly named local file.

The DNS evidence owner preserves exact confirmed-IPAM digest binding, one-family registration semantics, required authoritative observations and release/tombstone ordering. The IPAM owner preserves allocation confirmation digests, cleanup/reuse quarantine and opaque external references without exposing assigned values. These are read-side consistency controls, not authentication of the external service.

## Packaging and retirement

CI and current commands use `python -m provisioner.allocations.<owner>` for package CLIs. Installed-distribution checks build an sdist and wheel outside the checkout, block legacy `tools`/`scripts` imports while loading the owners, require package assets, and verify the retired script modules are absent. Reused build staging removes retired source/bytecode.

B05 is still open for direct operator/execution tools and retained-state conversion. B23 still requires transactional live reservation/IPAM/staging composition, authoritative owner receipts and observed cleanup. No deployed service or native platform is qualified by these module moves.
