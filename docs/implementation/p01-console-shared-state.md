# P01 Console shared session and cache state

Owner: Console/SRE; packages P01.02/P01.05/P01.06, requirements R02/R29.
The Console selects PostgreSQL sessions and cache by default. Its only connection
uses `console_runtime` in `console`, verified TLS and a mounted password. The
controlled owner migration creates `app.sessions`, `app.cache` and `app.cache_locks`;
replicas have DML only. Compose and Kubernetes run that same owner migration before
applications are installed. Tests that do not install dependencies explicitly select
array storage; this is a test setting and is not a production fallback.

Session payloads are encrypted with the Console's separate Laravel application key.
A restart must retain both the database and its declared key set. Loss or replacement
of that key invalidates sessions; recovery never substitutes another service's key.
Cookies remain Secure, HttpOnly and SameSite=Lax. There is still no login/delegation
journey in this P01 foundation, so anonymous session persistence is not identity
integration or revocation qualification.

`TenantCache` takes freshly authorized tenant scope on every call; it stores no
ambient tenant state. The same logical key produces separate tenant cache/lock keys.
Cache values expire within 30 minutes; locks within 30 seconds. Cache and locks never
serve as a durable idempotency or authorization record. Scheduler behavior remains
unimplemented until an actual owner task is introduced.

The Compose campaign invokes the built Console from separate processes, records
both tenants, rejects a conflicting lock and a foreign lock release, checks encrypted
session bytes, and rechecks the same state after database and Console restarts.
Results will be registered only after hosted execution. Existing database-role and
cross-service denials still apply; no additional database network access is granted.

The image-only HTML probe has no network or database by design. It first asserts
the production database defaults, then explicitly uses array storage solely for
markup/assets. The first image check at `715c242` correctly failed when this test
adapter still assumed file sessions. Package/browser checks passed; this probe
correction does not change the deployed database requirement.

The extended [foundation operations runbook](../operations/runbooks/foundation-operations.md)
also measures an invalid Console configuration and restoration of its original key,
plus Kubernetes failed-template rollback. HTTPS receipt/acknowledgement is exercised
against a synthetic receiver when the real database outage is observed. External
on-call routing and human acknowledgement remain separate operated inputs.
