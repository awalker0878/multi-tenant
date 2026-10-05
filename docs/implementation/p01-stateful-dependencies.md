# P01 stateful dependency integration

P01.05, with receiving P01.02/P01.03/P01.06 work. Owners: SRE and the Catalogue,
Planning, Lifecycle and Assurance service owners. Requirements R02/R15/R29/R35;
criteria G01.02/G01.05/G01.06. R15/R35 and G01.03 receive groundwork only; product
contracts and messaging remain unimplemented. The approved development baseline
selects RabbitMQ and Temporal. EV-P01-014 now retains a passing installation,
identity-isolation, restart and selected-object recovery campaign. P01 remains in
progress and G01 remains unreviewed.

## Candidate inputs and source basis

Checked 2026-10-05 against primary sources:

| Dependency | Development candidate and basis |
| --- | --- |
| RabbitMQ | [4.3.6](https://www.rabbitmq.com/release-information), selected event transport; verified TLS, imported users/vhosts and explicit queue/exchange permissions |
| Temporal | [1.32.0](https://github.com/temporalio/temporal/releases/tag/v1.32.0), using separate supported server and admin-tools images; explicit private PostgreSQL schema setup and restricted runtime credentials |
| Evidence storage | MinIO [security-fixed source release](https://github.com/minio/minio/releases/tag/RELEASE.2025-10-15T17-29-55Z), commit `9e49d5e7a648f00e26f2246f4dc28e6b07f8c84a`; build from source because this release directs container users to build it rather than consume an older prebuilt image |
| Build tool | Go [1.27.1](https://go.dev/doc/devel/release#go1.27.1); replayed fixed platform manifest and verified source archive hashes |
| Clients | Pika 1.4.4, Temporal Python 1.34.0, Boto3 1.43.108, PyJWT 2.15.1, Psycopg 3.3.6 and JSON Schema 4.26.0; exact transitive wheel hashes are observed into a private integration-driver lock |

The source-built object store is a disposable S3 behavior fixture. It does not select
a production vendor, support service, security certification, key custodian or
retention authority. Its AGPL source and exact source/build closure remain explicit.
Product dependencies do not import this integration-driver environment.

The [candidate inventory](../../deploy/dependencies/stateful/candidates.json) and
[observation workflow](../../.github/workflows/p01-stateful-inputs.yml) collected actual
platform manifests, both source-archive checksums and client closure. The
[immutable lock](../../deploy/dependencies/stateful/inputs.lock.json) binds four
Linux/amd64 image manifests (RabbitMQ, Temporal server, Temporal admin-tools and Go),
MinIO server/client source archives and the client wheel closure. The existing pinned
Python, uv and PostgreSQL inputs are included in the runtime report. Image tags alone
are not the replay identity.

Required controls follow RabbitMQ's [TLS](https://www.rabbitmq.com/docs/ssl),
[access controls](https://www.rabbitmq.com/docs/access-control) and
[definition import](https://www.rabbitmq.com/docs/definitions) interfaces. Temporal's
[service configuration](https://docs.temporal.io/references/service-configuration)
distinguishes TLS client authentication from its JWT claim mapper and authorizer;
a client certificate alone does not establish namespace authorization. The deployment
must explicitly enable the authorizer and exercise wrong-namespace/invalid identity
cases. Private synthetic trust material is not operated issuer integration.

## Session and cache inventory

The measured Console foundation uses a file session driver inside a disposable
single replica. This is not shared-session readiness. The selected implementation
path is service-owned PostgreSQL session/cache tables, using the existing private
Console database and restricted runtime role; a separate Redis/Valkey deployment is
not required by the accepted architecture. Implement and measure shared-session
persistence and isolation before claiming that P01 dependency requirement complete.
Authentication/session revocation semantics remain P02 obligations.

## Input discovery correction

Run [37250318779](https://github.com/awalker0878/multi-tenant/actions/runs/37250318779)
failed before installation: the proposed Temporal auto-setup 1.32.0 image does not
exist. The upstream docker-builds project deprecates auto-setup. The corrected
candidates use the supported server/admin-tools images separately. This failure is
not an installation or authorization pass. Resolver commands now retain both output
streams and exit status, including failed commands.

Run [37250759053](https://github.com/awalker0878/multi-tenant/actions/runs/37250759053)
resolved the supported Temporal server image, then the MinIO client Quay endpoint
returned HTTP 401. The next attempt used the Docker Hub repository linked
by the [upstream client guide](https://github.com/minio/mc#docker-container).
No credentials were added and no registry authentication was bypassed.

Run [37250876554](https://github.com/awalker0878/multi-tenant/actions/runs/37250876554)
also could not retrieve the public MinIO client image from Docker Hub. Both published
client image endpoints were unavailable to this unauthenticated CI runner. The client
is built from release commit `7394ce0dd2a80935aded936b09fa12cbb3cb8096`
using the same verified Go toolchain and fixed source checksum as the server workflow.
The fixture does not require private registry access or credentials.

## Locked inputs and measured campaign

[Input observation 37251624593](https://github.com/awalker0878/multi-tenant/actions/runs/37251624593)
passed at source `1ad067ec2d1dd3b1faf73a66ab7fa45b90e00307`. Its
[retained retrieval record](https://github.com/awalker0878/multi-tenant/blob/0ab20b97dd3ac60e10d1d890de27c4033b5a2c43/verification/p01/stateful-inputs/run-37251624593/retrieval.json)
and the four preceding failed input attempts preserve actual resolver output. The
resolver runs the pinned uv binary inside the pinned Python image; the preceding
standalone uv invocation lacked the operating-system utilities needed for resolution.

The [private fixture](../../deploy/fixtures/stateful/README.md),
[campaign](../../scripts/p01/run_stateful.py) and
[integration workflow](../../.github/workflows/p01-stateful-integration.yml) install
real dependencies with no host-published ports. Probes exercise scoped broker users,
Temporal namespace JWT authorization and separate PostgreSQL roles, and retained S3
versions restored to an empty second store. The probe clients are support tooling;
product services do not import them.

[Run 37254627255](https://github.com/awalker0878/multi-tenant/actions/runs/37254627255)
passed at source `72706e029b06345caa88608099c3137431ba1d10`. The
[retained EV-P01-014 record](https://github.com/awalker0878/multi-tenant/blob/eb062d9372430fa6d8b3af94eac995969e1621e0/verification/p01/stateful/run-37254627255/retrieval.json)
binds the workflow, artifact archive, command streams and source tree. Examination
verified all **40 campaign checks**, **73 live probe assertions**, **67 bounded command
outcomes**, **134 command-log hashes** and **48 immutable source bindings**. Campaign
checks include probe execution; these counts must not be added as independent tests.
Cleanup completed with no retained credential-bearing output or remaining project
containers, networks or volumes. The earlier complete pass at
[run 37254034761](https://github.com/awalker0878/multi-tenant/blob/eb062d9372430fa6d8b3af94eac995969e1621e0/verification/p01/stateful/run-37254034761/retrieval.json)
is retained separately; the final replay adds exact SQL rejection diagnostics and
corrects a noisy local readiness identity.

| Measured boundary | Observation |
| --- | --- |
| Private installation | Empty disposable volumes; separate internal dependency networks; no host-published ports; actual input hashes and built image configuration IDs retained |
| PostgreSQL | TLS 1.3; separate Temporal/visibility databases; runtime DML with separate schema owners; migrator logins disabled after bootstrap. Five SQL negatives retain exact DDL, role, foreign-database, wrong-password and plaintext rejection diagnostics; DDL/role failures have SQLSTATE 42501. The required timestamp conversion function is granted to the visibility runtime and denied to PUBLIC and the foreign runtime |
| Broker authority | TLS AMQP; plaintext disabled; publisher/consumer permissions separated; foreign vhost and invalid password denied; management and metrics inaccessible from client networks |
| Broker restart/revocation | Confirmed persistent message survives restart with identical unacknowledged bytes and redelivery flag; acknowledgement empties the queue. Deleted publisher remains rejected after another restart; unchanged bootstrap definitions do not recreate it |
| Workflow authority | TLS frontend and explicit JWT authorizer; missing, foreign-namespace, expired and wrong-audience tokens denied; worker cannot administer namespaces; internal RPC listeners inaccessible to clients. Public GetSystemInfo negotiation grants no namespace access |
| Workflow recovery | Worker and Temporal/PostgreSQL stop/restart; the same waiting workflow/run resumes, completes after a signal and appears completed in private visibility storage. Withdrawing its issuer key rejects the old token after a server restart |
| Object authority/retention | Scoped tenant prefixes; foreign reads/writes, bucket listing, version deletion and invalid identity denied. Even bootstrap administrator deletion and retention shortening fail with HTTP 400/InvalidRequest and the exact WORM diagnostic; bytes and deadline remain unchanged |
| Selected-object restoration | The original 77-byte version survives a newer PUT and restart. Its captured bytes restore into an independent empty store under a new version ID, with original identity metadata and equal-or-longer COMPLIANCE retention; administrator denial and another restart preserve it |
| Object revocation/outages | Disabled runtime identity fails before and after restart while administrator readiness succeeds. Stopped broker/workflow/store produce separately classified transport failures; those failures are not authorization evidence |

The final evidence capture has SHA-256
`f24d45a5b34c6d3e308d574c56588bc8be58f5d747565f6c3701725afed46ef4`,
source version `d824e6b8-563a-47fe-a1e2-31f51e533a76` and restored version
`0cdbbd62-3a90-4475-94f4-619c8e0df0ca`. Retention extends from
`2026-10-06T02:17:53.186000+00:00` to `2026-10-06T02:18:10.153000+00:00`.
Workflow execution `p01-restart-witness` / `01a109da-6e00-7c3b-b19e-e517e2092743`
is identical before and after restart. The
[probe observations](https://github.com/awalker0878/multi-tenant/blob/eb062d9372430fa6d8b3af94eac995969e1621e0/verification/p01/stateful/run-37254627255/probe-observations.json)
retain each result and its raw stdout hash.

## Failed runtime attempts and corrections

All five failed attempts remain available in the
[immutable failure evidence](https://github.com/awalker0878/multi-tenant/tree/04c35a16250bb7cf7a899d6d0a2ebad31c9c6db7/verification/p01/stateful).
No partial run becomes a pass.

| Run | Failure and correction |
| --- | --- |
| 37251772917 | Broker readiness used the wrong listener address; use authenticated node health and loopback listener connectivity |
| 37252352211 | Temporal SDK timeout/configuration did not match the pinned version; use the supported call timeout and configuration polling interval |
| 37252715903 | Expired-token rejection occurred during SDK negotiation and visibility lacked its required function grant; separate public negotiation from namespace RPC identity and grant only the visibility runtime |
| 37253200622 | Retention correctly rejected administrator deletion with InvalidRequest, while the probe expected AccessDenied; require the observed WORM code/message plus unchanged object/deadline |
| 37253550966 | A CLI failure printed a generated credential; the artifact guard withheld that stream and failed cleanup qualification. The CLI wrapper now retains private diagnostics and emits only exact-secret-redacted failures. This run remains failed despite resource removal |

## Remaining work and replay

Follow the [recovery runbook](../operations/runbooks/stateful-dependency-recovery.md)
to replay this source with fresh synthetic credentials and empty volumes. Preserve
the distinct source, image, object-version and workflow-run identities in each record.

This is single-node Compose evidence for one selected object version and synthetic
dependency clients. It establishes neither whole-store/all-version restoration nor
production IAM, issuer latency, regulatory retention, HA, RPO/RTO or operated vendor
adoption. No native platform activity occurred. Product versioned contracts and
transactional outbox/inbox (P01.03), shared Console PostgreSQL sessions/cache, actual
alert receipt, remaining deployment recovery, promotion trust and G01 review remain
open. Earlier Compose/Kubernetes and Permit Desk records retain their original scopes.
