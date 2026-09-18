# Execute and review the routed IPv6 laboratory

**Scope:** disposable local Linux packet experiment for the existing WD14 design.
This command does not provision a native vendor platform or contact a real target.
It is an implementation/qualification work package beneath the
[IPv6 engineering profile](../engineering/routed-ipv6-qualification.md), not a new
hosting controller, service contract or production firewall installer.

## Prerequisites and privilege boundary

Use an explicitly authorized disposable Linux worker with Python dependencies from
`requirements-repository.txt`, iproute2, util-linux `unshare`, and nftables. The worker
must permit creating separate user/network namespaces and changing the **new node
namespaces'** IPv6 sysctls. Read-only `/proc/sys` or missing namespace capabilities
are blockers; the harness never remounts proc, disables AppArmor or changes a
controller-wide security policy. It never attaches its bridges to a host NIC.

The hosted workflow uses the standard disposable `ubuntu-24.04` virtual machine,
read-only repository permission, no target credentials and no persisted checkout
credential. Its two named laboratory commands run with explicit `sudo` because the
unprivileged namespace mapping was denied on the observed hosted image. This is an
intentional privileged test job, not a transparent retry or a production runner.
Do not move it to a self-hosted privileged controller or grant it site network access.

The first hosted attempt was blocked before any packet scenario by a denied uid-map
write. The next explicit-privilege attempt exposed a source-directory permission
boundary: mapped root could not traverse the runner-owned checkout. CI now stages
only `git archive HEAD` in its own root-owned temporary directory, rather than
changing the runner home or checkout permissions; it removes that directory afterward. The authoring container separately lacked nftables and exposed read-only
sysctls. Those attempts are not passing evidence. The approved disposable-runner
privilege is supplied explicitly by the workflow, while every data-path worker still
requires a different network namespace from both the original controller and master.
[GitHub's hosted-runner administrative model](https://docs.github.com/en/actions/reference/runners/github-hosted-runners)
and [Ubuntu's namespace restriction description](https://ubuntu.com/blog/whats-new-in-security-for-ubuntu-24-04-lts)
explain the runtime distinction; they do not guarantee this campaign will pass on a
future kernel/image.

## Run without introducing actual inputs

From the repository root in the accepted worker:

```sh
python -m unittest discover -s tests -p test_ipv6_packet_fixture.py -v
python lab/run_ipv6_lab.py --execute --output build/reports/local_ipv6_packet_lab.json
```

The first command is offline source/message/guard testing, not kernel packet evidence.
The second creates and tests the exact source-hash-bound topology. On the hosted CI
worker the workflow invokes this same fixed command through its named privileged
step; it does not accept a remote inventory, target URL or supplied address. Invoking
the command without `--execute` makes no topology or report. An existing report path
is refused so a rerun cannot silently replace prior evidence. Use a new output name
for a later deliberate observation.

`--inner` is an internal subprocess entry, not a bypass: it requires the parent
namespace identity and a new master namespace containing only loopback. Private
workers then require their own new namespace. Reports omit credentials and actual
host topology, retaining configuration fingerprints and the synthetic reference
observations. These guards prevent accidental scope expansion; they are not a
security sandbox against an administrator who changes the code.

## Actual steps and evidence

| Phase | Required observation | A failure means |
|---|---|---|
| Construction | Hash-bound source, fresh namespaces, installed default-drop policy, exact IPv6 addresses after DAD, healthy local challenge endpoints, no global IPv4 addresses | Stop or fail; do not turn a missing target into a denial pass |
| Initial quarantine | Intended processor-to-data request denied with edge drop increment | Denied preparation has not been demonstrated |
| Declared flows | Both tenant application paths and four clients' IPv6 DNS UDP/TCP/fallback requests succeed | Family/service path not operational |
| Negative paths | Wrong port, unsolicited reverse and unbound service probes fail with healthy controls and edge counters; cross-tenant probes have no route and healthy target | Boundary or test attribution is incomplete |
| Local control | Actual neighbours and one RA rejection with unchanged endpoint routes | Static IPv6 assumptions not demonstrated |
| Dependency failure | Removing one origin-specific DNS reply route affects only its intended tenant, then exact restoration works | Reply isolation or recovery incomplete |
| Containment | Existing and new traffic stop before established acceptance while the other tenant remains healthy | Containment precedence not demonstrated |
| Link failure | No alternate permit path; explicit link/address/route reconciliation recovers | The tested failure behaviour differs |
| PMTU | Large transfer fails when PTB is blocked despite healthy small traffic; restoration permits it with observed 1280-byte MTU | Do not hide an ICMPv6/MTU dependency behind a simple ping or TCP-connect result |
| TLS | Actual routed TLS1.3 identity and negative cases, including grant withdrawal; temporary credential files removed | Service identity is not demonstrated on the route |
| Cleanup | Worker processes stop and original controller configuration fingerprints match | Entire campaign fails even if earlier probes passed |

The UDP-to-TCP DNS case deliberately scripts a truncated UDP answer; the sockets and
fallback exchange are real, but this is not a large-response fragmentation test.
Port 443 challenge targets do not assert that the unselected time/log/repository
services use that protocol. The lab admits no such service flow.

## Interpret and retain results

`PASSED_IPV6_FIXTURE` means all enumerated local observations passed and the original
network configuration was unchanged. A failed observation, incomplete execution,
missing prerequisite, timeout or changed original configuration returns nonzero.
The report records kernel/nft versions, exact fixture and implementation hashes,
per-observation details and explicit non-qualification limits. It is not a signed
approval, authoritative native inventory or proof of universal IPv6 correctness.

The GitHub job re-executes the retained IPv4 packet/TLS fixture as a separate family
regression. Both commands must pass; the IPv6 command can still run for diagnosis
after an IPv4 failure, but that does not turn the job green. Only the two synthetic
reports are handed back to the unprivileged artifact uploader. Runtime certificates,
keys, sockets, provider state and actual inventories are not uploaded.

`python scripts/check_routed_lab_results.py` independently requires all 47 IPv4
and 49 IPv6 observation records, ordered IDs, unchanged-controller indicators, exact
current source hashes and the positive PMTU witness. Empty/partial reports and
summary-only PASS labels fail. It verifies record consistency, not execution
authenticity or approval.

Inspect reports against the exact PR head/run and verify the artifact digest before
recording a result. A later source change needs a later successful run. Historical
`quality/` files and the original I08 delivery columns are not rewritten. Keep the
native offered-family acceptance open until the installed stack, complete dependency
paths, management exclusion and recovery behaviour are qualified separately.

The [native address-family assurance gate](../engineering/native-ipv6-address-family-assurance.md) consumes later native evidence and deliberately does not treat this Linux namespace result as production family qualification.

[Engineering basis and exclusions](../engineering/routed-ipv6-qualification.md) · [Test families](../assurance/verification-families.md)

## Engineering issues demonstrated during development

An initial routed trial passed its first 36 observations but stopped at route recovery:
link-up alone did not restore the lost IPv6 address/connected next-hop context. The
corrected sequence reapplies the exact source address, observes DAD completion and
then reconciles the declared routes. The successful report records the empty
pre-recovery address state and the same recovered address. This is a measured
Linux recovery behaviour, not an assumed native vendor lifecycle guarantee.

The first complete campaign is bound to commit
`95305d1eea341bfa5530a475c80119de40961d23`,
[run 35334038221](https://github.com/awalker0878/multi-tenant/actions/runs/35334038221).
Its 49 IPv6 and 47 IPv4 observations passed on the recorded worker, and the source
hashes were inspected against the actual files. Later documentation, report-checker
or code revisions still require a successful exact-head run before merge. The
work-package record retains the original artifact digest; it does not issue native
qualification or overwrite earlier failed/blocker evidence.
