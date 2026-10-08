# P01 retained evidence byte integrity

P01.04; examination 2026-10-05. The resumed checkout matches the active remote
source except for generated Planning package metadata and 18 retained build logs.
The original local log bytes match their campaign/retrieval SHA-256 values. The
remote versions exactly match a carriage-return-to-newline conversion of those
bytes. Earlier text-mode upload preparation changed the logs, without changing the
original reports. This affected the messaging, Compose, Kubernetes and corrected
artifact-trust runs; the original execution results are not rerun or reclassified.

The repair restores the original bytes through the GitHub connector's base64 blob
operation. Each returned Git blob ID is compared with the independently computed
Git blob ID before the tree is committed. No recorded digest is weakened or
rewritten to match the altered file. Generated package metadata is left alone.

`python3 scripts/p01/verify_retained.py` verifies every existing P01 retrieval
record that declares `retained_file_sha256`: 55 records and 6,262 file bindings at
this examination. It reads bytes, rejects missing files, unsafe paths and symlinks,
and fails if any digest differs. Six regression tests include the exact text-mode
normalization failure. Normal architecture/documentation CI now runs both checks.

This proves consistency of retained bytes with the declared inventories. It does
not independently authenticate a workflow, trust an edited inventory, replay an
image whose layers are not retained, or supply gate approval. Older records using
other retention schemas still require their documented verification procedures.
Changes to this verifier, the inventories or CI remain subject to the separate
trusted-base policy and actual review/protection activation.

The publication mechanism follows the [GitHub blob API](https://docs.github.com/en/rest/git/blobs#create-a-blob).
