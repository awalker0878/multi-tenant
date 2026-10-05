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
| Revocation and drift | Old health token rejected after rotation; replacement accepted; revoked database login and schema drift produce unavailable health; restoring each recovers health |
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
