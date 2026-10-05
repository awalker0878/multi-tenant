# P01 isolated runtime integration

P01.02/P01.05 are in implementation. This record separates implemented source from
measured installation evidence; it does not pass G01.02/G01.05.

The first topology connects seven application foundations to private PostgreSQL
databases using TLS with server-name verification, separate runtime/migrator logins
and per-service mounted credentials. A private `/health/dependencies` diagnostic
authenticates its caller and checks the owned schema version. `/health/ready`
continues to report unavailable product readiness. A dependency diagnostic grants
no tenant, application, worker or native authority.

PHP services use their existing FPM image through restricted TLS ingress. Python
services add a pinned ASGI runtime and PostgreSQL client; their original diagnostic
CLI and disabled worker-task behavior remain distinct. The synthetic installation
generates secrets outside source/images and records non-secret configuration and
artifact identities only. Real operated issuer/custody, signed promotion, broker,
Temporal, evidence-store and full application recovery qualification remain
subject to their own implementation and measured checks.

## Package and image observations

Source `c28c87e6c6804450fea9f6d6817a818eed37fc03` passed all nine private package
checks and all nine restricted image checks. The three Python applications now
install their locked Uvicorn/PostgreSQL runtime dependencies into their owned image;
their package campaign also starts the installed HTTP server and observes liveness,
unavailable product readiness, denied diagnostic credentials and unavailable database
health. The four PHP applications retain their normal Laravel/FPM entrypoints and
exercise the new Foundation Actions/adapters through their private test suites.

| Observation | Immutable retained record | Examination |
| --- | --- | --- |
| Nine package checks | [Run 37244794879](https://github.com/awalker0878/multi-tenant/blob/ea1e98d7f0060faf4f13f0c55482db17e48a1c3a/verification/p01/packages/run-37244794879/retrieval.json) | 173 command outcomes, 346 command-log hashes, 388 artifact hashes and 293 unique source bindings |
| Nine image checks | [Run 37244794860](https://github.com/awalker0878/multi-tenant/blob/ea1e98d7f0060faf4f13f0c55482db17e48a1c3a/verification/p01/images/run-37244794860/retrieval.json) | 86 command outcomes, 172 command-log hashes and 198 unique source bindings |
| Earlier PHP failures | [Run 37244201538](https://github.com/awalker0878/multi-tenant/blob/ea1e98d7f0060faf4f13f0c55482db17e48a1c3a/verification/p01/packages/run-37244201538/retrieval.json) | Original formatting and enum/final-class rule failures preserved separately; corrected tests passed in the later source-bound run |
| Initial Compose failure | [Run 37244794937](https://github.com/awalker0878/multi-tenant/blob/ea1e98d7f0060faf4f13f0c55482db17e48a1c3a/verification/p01/local/run-37244794937/retrieval.json) | Initial PostgreSQL volume ancestry permissions prevented startup; failure logs, seven embedded image reports and cleanup outcome retained unchanged |

These package and image checks establish their measured build/process scope. Local
image configuration IDs do not establish published manifest identity, signature or
promotion. Later changes require the affected checks again.

## Installation boundary

[The local campaign](../../deploy/local/README.md) generates an absent private runtime
directory, verifies application ownership/source labels, installs observed immutable
PostgreSQL and Nginx manifests, and creates separate service database, runtime and
migration identities. Runtime credentials cannot create schema objects, change schema
metadata or assume the owner role. Migrators explicitly assume their service's NOLOGIN
owner. TCP database access requires TLS and the matching database/identity pair;
applications also verify the server certificate and DNS name.

Mounted health credentials authorize only `/health/dependencies`. They are not OIDC,
tenant sessions, delegated application authorization or worker authority. The schema
fixture contains two tenant-keyed records; it does not implement row-level tenant
authorization or the carried Permit Desk application/configuration restore fixture.

The installation campaign measures actual authentication, TLS, cross-database/DDL
denial, revocation, schema drift, dependency loss and database restart behavior. A
passing diagnostic still leaves `/health/ready` at HTTP 503 and workers unable to
consume tasks. Completed observations and remaining limitations are recorded below;
an unexecuted check never becomes a pass.

## Measured Compose installation

The [passing installation record](https://github.com/awalker0878/multi-tenant/blob/f2f9e863c9579d7456f0838f0a355523264dc7cc/verification/p01/local/run-37245534459/retrieval.json)
binds run `37245534459` to source `e9eac175f2fb845847aa5954522a8470260180dc`.
All 126 checks and 127 installation command outcomes passed; the unique installation,
volume and private credentials were removed successfully. The retained artifact also
includes seven passing image builds. Examination verified 386 command-log hashes,
195 unique source bindings, the rendered configuration digest and the original archive.

| Measured boundary | Actual observation |
| --- | --- |
| Empty installation | Seven built application images; private PostgreSQL databases and identities; seven authenticated TLS migrations; seven restricted TLS proxies |
| Diagnostic contract | Each service returns 401 for absent/wrong credentials, 200 for its healthy owned dependency, 200 for process liveness and 503 for product readiness |
| Console through ingress | HTTPS server-rendered Foundation page, Secure/HttpOnly/SameSite=Lax session cookie, and compiled JavaScript/CSS served with correct media types; no JavaScript execution claimed by this check |
| Database authority | Runtime DML succeeds in a rolled-back transaction; schema creation, metadata mutation and owner-role assumption fail; foreign database, wrong password and plaintext connections fail |
| Ingress restriction | Only loopback TLS ports are published; backend ports remain unpublished; foreign Host and source/configuration paths are denied; an untrusted CA is rejected |
| Revocation and drift | Governance rejects its old health token after rotation and accepts the replacement; revoking its database login makes health unavailable. Planning schema drift also makes health unavailable. Restoring each recovers health |
| Dependency loss and restart | Stopping PostgreSQL makes all seven dependency probes unavailable while process liveness remains available; restart restores health and exact tenant-keyed record digests |

The earlier [second failed attempt](https://github.com/awalker0878/multi-tenant/blob/f2f9e863c9579d7456f0838f0a355523264dc7cc/verification/p01/local/run-37245241548/retrieval.json)
is also retained unchanged. Correcting PostgreSQL-owned volume ancestry allowed the
seven migrations to complete; that attempt then failed at host-port discovery on
internal-only proxy networks. The passing source adds a separate ingress bridge for
each proxy, with masquerading disabled, while every application/database network
remains internal. Explicit ephemeral loopback publication and process/port diagnostics
are part of the corrected source.

This is reproducible development installation evidence, not operated deployment or
complete P01 acceptance. The two tenant-keyed records are a database fixture only.
Database restart is not backup restoration. Complete Permit Desk application/configuration
recovery, broker/outbox/inbox, Temporal, evidence storage, signing/promotion, alert receipt,
failed-deployment recovery and independent gate review remain outstanding.

## Corrected connection-timeout replay

The first Kubernetes run reached installed workload readiness but failed because the
test harness incorrectly required a Python-specific response field from PHP. Its
[unchanged failed evidence](https://github.com/awalker0878/multi-tenant/blob/2a024a7848bcc575213c0b98f3fa6b391e4b6300/verification/p01/kubernetes/run-37245679773/retrieval.json)
also records the first observed Cilium chart archive and OCI identities. The corrective
source checks each language's actual health contract and replays those pinned chart
identities.

The [second Kubernetes attempt](https://github.com/awalker0878/multi-tenant/blob/5dec1016aa5737d7728f31094efcfbfcec3f3dd4/verification/p01/kubernetes/run-37246349799/retrieval.json)
recorded 136 passing checks, including eight permitted network connections and fifteen
denied connections, before its first database-outage PHP probe exceeded the 30-second
outer timeout. Its seven retained migrator outputs independently identify each owned
database, its matching migrator login and schema version 1. This attempt remains failed.

The [pinned PHP driver implementation](https://github.com/php/php-src/blob/php-8.5.11/ext/pdo_pgsql/pgsql_driver.c)
appends the PDO timeout option after the supplied connection string. The original
connection-string value was therefore overridden by the driver's default. Source
`c9c202786437601c0f000bdf29d7e1e401e773ee` sets `PDO::ATTR_TIMEOUT` to two seconds,
forces the selected TLS transport, and applies read-only/query limits during connection
startup. Its real loopback regression accepts TCP without answering the PostgreSQL TLS
request; every PHP service must return sanitized unavailable health within five seconds.
The test also inspects the actual TLS request, so an early configuration failure cannot
count as a successful timeout observation.

| Corrective replay at c9c202 | Retained result |
| --- | --- |
| [Nine packages — run 37247300537](https://github.com/awalker0878/multi-tenant/blob/60423fa2639a14026f59d5aaf75ce23011174fb3/verification/p01/packages/run-37247300537/retrieval.json) | All pass, including four real stalled-TLS regressions; Console 40 tests/177 assertions, each other PHP service 30 tests/135 assertions; 298 unique source bindings and 346 command-log hashes checked |
| [Nine images — run 37247300526](https://github.com/awalker0878/multi-tenant/blob/60423fa2639a14026f59d5aaf75ce23011174fb3/verification/p01/images/run-37247300526/retrieval.json) | All pass; 198 unique source bindings and 172 command-log hashes checked |
| [Compose — run 37247300528](https://github.com/awalker0878/multi-tenant/blob/60423fa2639a14026f59d5aaf75ce23011174fb3/verification/p01/local/run-37247300528/retrieval.json) | All 126 checks pass with cleanup completed; 202 unique source bindings and 386 command-log hashes checked, including its seven embedded image campaigns |

The connection-establishment observation and PostgreSQL statement limit do not establish
a universal wall-clock bound for DNS failure or interruption of an established socket.
Those fault modes require their own measured cases. The Kubernetes campaign additionally
requires each directly executed dependency probe to finish within five seconds.

## Measured Kubernetes installation

The [passing Kubernetes record](https://github.com/awalker0878/multi-tenant/blob/08aab461490849f1e1f9c2874049c4d45796d75b/verification/p01/kubernetes/run-37247300531/retrieval.json)
binds run `37247300531` to the corrected source `c9c202786437601c0f000bdf29d7e1e401e773ee`.
All 157 checks and 315 installation command outcomes passed. Seven embedded image
campaigns also passed; examination verified 762 command-log hashes and 200 unique
source bindings. The disposable cluster, runtime and credentials were removed.

| Measured boundary | Actual observation |
| --- | --- |
| Cluster and image inputs | kind v0.33.0, Kubernetes v1.36.4 and Cilium 1.20.2; observed chart archive and OCI identities replayed unchanged; immutable rendered Cilium images; both nodes contain the expected application/dependency image configuration identities |
| Installation and migrations | Seven applications/proxies and private PostgreSQL become ready; seven migration Job outputs identify the owned database, matching migrator and schema version 1 |
| HTTP and database authority | All seven applications pass their owned authenticated health contracts, invalid/absent identity, TLS trust, Host/source restrictions and unavailable product readiness checks; runtime DML succeeds while DDL, metadata mutation, owner-role, foreign-database, plaintext and wrong-password attempts fail |
| Cilium policy | Eight allowed connections: seven diagnostic Pods to their own proxy and Planning to PostgreSQL. Fifteen denied connections: seven diagnostic Pods to a foreign proxy, seven to PostgreSQL, and Planning to Governance. Denials require actual connection timeouts; DNS failure or connection refusal does not count |
| Revocation | Governance's direct probe fails after login revocation and recovers after restoration, in 0.137 and 0.138 seconds respectively |
| Database outage | Direct PHP dependency probes fail in 2.129–2.148 seconds and Python probes in 2.270–2.286 seconds, all below the five-second bound; application process liveness remains available |
| Persistent restart | PostgreSQL is scaled down and recreated on its existing PVC; all seven services recover healthy dependencies and retain identical ordered fixture bytes. Examination compares the actual fourteen before/after SQL outputs, not only the runner's result flags |

The [migration observations](https://github.com/awalker0878/multi-tenant/blob/08aab461490849f1e1f9c2874049c4d45796d75b/verification/p01/kubernetes/run-37247300531/migration-observations.json)
bind the seven parsed identity/version rows to their raw Job-log hashes. Kubernetes
removes unready application endpoints, so outage observations deliberately execute the
actual dependency probe in each application container; they do not claim the proxy
continues returning the application's unavailable-health response during that outage.

This closes the measured first Compose/Kubernetes foundation increment. P01.02/P01.05
and the P01.06 recovery package remain in progress; G01 remains unreviewed. Additional
network paths, Kubernetes schema/secret fault cases, the complete Permit Desk fixture,
broker/Temporal/evidence-store behavior, backup restoration, alert delivery, independent
deployment recovery and operated trust/admission still require their own work and evidence.

## Complete Permit Desk application recovery follow-on

[The dedicated fixture record](p01-permit-desk-recovery.md) now retains EV-P01-013:
79 passing application/configuration recovery checks, two actual backup restores
into fresh Compose installations, full logical/file equality, tenant/role denials,
a post-restore write and failed-configuration recovery. This adds the previously
missing application fixture; it does not change the scope of earlier foundation
restart observations or add a Kubernetes fixture-restore claim. Its dependency,
evidence-store, alert and trust limitations remain part of that record.

## Stateful dependency and selected-object recovery follow-on

[The stateful dependency record](p01-stateful-dependencies.md) retains EV-P01-014:
40 campaign checks and 73 live probe assertions pass for pinned RabbitMQ, Temporal
with private PostgreSQL, and two source-built S3 fixtures. The record measures scoped
identity denials, broker redelivery, restart-persistent credential revocation, completion
of the same workflow execution and restoration of a selected retained object version
to a fresh store with identical bytes, original identity metadata and preserved retention.
The 134 command-log hashes and 48 source bindings have been verified against retained
bytes and the immutable source tree; cleanup completed.

These are separate synthetic dependency probes. They add no product messaging,
Kubernetes dependency-installation, whole-store recovery or operated adoption claim.
Shared Console sessions/cache, service-owned versioned contracts/outbox/inbox, actual
alert receipt, remaining deployment recovery and admission/promotion trust remain open.
G01 is still unreviewed.
