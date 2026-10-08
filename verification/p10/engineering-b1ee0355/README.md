# P07/P08 transport correction and P10 engineering rerun

Source: `b1ee0355580f06620fc723f7120f11725fade743`.
Candidate version 2: `4d48a81d3a44a807a80cd2cebc97055ec419d2cd6aa0c355d73af067e3241e03`.

[P10 run 37708345920](https://github.com/awalker0878/multi-tenant/actions/runs/37708345920)
passes all nine commands and **1,050 component tests**: 325 Planning, 371 Lifecycle
and 354 worker tests, with zero failures, errors or skips. The 19 P10 tooling tests
also pass. All ten workflows pass on this exact source, including P07/P08/P09,
package/image/contract/policy checks and all three P06 browser journeys.

The worker now rechecks OpenStack/VMware/Glance credentials through request and
response completion, checks upload token expiry at every chunk, and verifies
mounted writer/observer independence before effects. Native JSON clients reject
incomplete declared lengths, ambiguous framing and truncated chunk streams.
Uncertain effects remain held without replay or automatic cleanup.

The first source `799740e9` failed worker qualification. Diagnostic source
`ce6bafba` exposed two incorrect test assumptions: an abruptly closed TLS stream
need not deliver all bytes previously passed to the local socket. Hosted receivers
observed 32,768 or 49,152 bytes where the test assumed 65,536. The corrected fixture
acknowledges the first complete chunk before triggering rotation or expiry. The
exact byte count and no-follow-up-import assertions remain; production controls
were not relaxed. Both original failures are retained.

`job.log` contains the decoded original passing job log. The three failure logs
preserve the initial result and diagnostic reruns. `observations.json` records
test totals, original log hashes, GitHub artifact metadata, measurements and limits.
`candidate.json` and `dossier.json` were generated from the clean checkout whose
tree matches the published source. `ci-observation.json` records all ten passing
workflow states. `local-qualification-tests.log` retains the
19 local qualification-tool results.

All 48 synthetic scheduler operations pass. The real single Lifecycle database
restore denies the old grant and preserves one accepted synthetic effect. These
results do not establish native capacity or coordinated control-plane RPO/RTO.
Artifact archive bytes have not been independently rehashed here; their digest is
GitHub-reported. The retained decoded logs and local records have separate hashes.

P07/P08/P09/P10 remain incomplete for native/operating acceptance. N01–N15 and
OP01–OP07 are unknown or unreviewed; selected owner protocols, real native campaigns
and receiving decisions remain outstanding. The actual dossier holds all six P10
packages and grants no native write or release authority.
