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
Temporal, evidence-store, Kubernetes and application recovery qualification remain
subject to their own implementation and measured checks.

Current source additions are awaiting the clean-install, authentication, TLS,
cross-database/DDL denial, revocation, schema-drift, dependency-loss and recovery
campaign. No unexecuted check is recorded as passing.
