# Repository-import evidence

[Release status](release_validation.json) separates actual local execution from blocked engines.
[Python/source results](local_validation.json), [source test log](local_test_output.txt),
[route model](reference_route_checks.json), [DNS wire](local_dns_transactions.json),
[HTTPS readback](local_native_readback.json) and [routed IPv4/mTLS](local_packet_lab.json)
record this run. Campaign counts overlap and are not additive unique coverage.

[Terraform](terraform_validation.json) and [Ansible](ansible_validation.json) are
blocked because their executables were unavailable; [installation attempts](toolchain_attempts.json)
are recorded separately. No mocked engine pass or generated provider lockfile is invented.

[Source lineage](../../sources/import_manifest.json) records every imported source disposition.
[Repository observation](../../sources/repository_observation.json) is a read-only GitHub snapshot.
No remote commit/push, native target contact or production deployment occurred.

Current reruns belong under ignored `build/reports/`. These are sanitized release
fixtures, not the location for live inputs, state, credentials or platform evidence.
The old `quality/` tree is historical and remains unchanged. Integrity hashes are
not signatures or evidence that an approving authority accepted the architecture.

[Extraction and local Git rehearsal](import_rehearsal.json) verifies copy-only import, preserved commit/index and byte-identical Git staging. The Git fixture was local and never contacted its configured remote.
