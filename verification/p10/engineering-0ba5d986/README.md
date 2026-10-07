# P10 source and evidence binding correction

Source: `0ba5d986d6ba20ec9303f016baf468cedaa3c352`.
Candidate version 2: `898258e049b83c8e7534139e0b153ae046b7c0a7c250fad7ff027f86f04e7f98`.

[Hosted campaign](https://github.com/awalker0878/multi-tenant/actions/runs/37704372041):
nine commands passed, with 325 Planning, 371 Lifecycle and 303 worker tests and
no failures, errors or skips. The campaign includes actual PostgreSQL/TLS/Cosign,
synthetic native owners, twelve-tenant scheduler measurements, a single-database
stale restore and a local alert receiver.

- `job.log` is the original decoded job log returned by the GitHub connector.
- `observations.json` records source, measurements, test totals, hashes and limits.
- `local-qualification-tests.log` retains all 19 P10 tooling checks against the same source.
- `dossier.json` records the actual unbound packet and all six held P10 packages.

The GitHub artifact metadata includes the archive digest and retention date. Its
signed download returned HTTP 403, so archive bytes have not been independently
rehash-verified here. The decoded log and local files have their own recorded hashes.

All fifteen native inputs and seven operating inputs remain unknown or unreviewed.
These observations establish E2 engineering behavior only. They do not supply an
installed platform, selected application/guest integrations, native throughput,
coordinated RPO/RTO, restricted installation, receiving people or a G10 decision.
