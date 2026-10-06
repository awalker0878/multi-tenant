# P03 Catalogue implementation

The requesting user authorized P03 development on 2026-10-05. The accepted G00/DC03 baseline supplies the ordinary workload, deployment and reference cardinalities. P01/P02 operating and independent receiving obligations remain open; this entry does not pass their gates.

P03.01–P03.03 now implement Catalogue-owned PostgreSQL tables, immutable full deployment intent, workload identity ownership, current-reference validation, one active deployment identity per application/environment, explicit same-tenant reference sharing, separate reference administration, application ETags, tenant/actor command receipts and atomic audit/outbox records. P03.02 preserves unsupported mandatory requirements and validates device order, dataset/service references, separate lifecycle dependency graphs, controlled inter-domain interfaces and ordinary NIC placement. Catalogue calls Governance for current delegation and bounded active-owner checks; provider identities and native effects remain outside Catalogue.

The strict intent schema is `contracts/schemas/catalogue/intent-v1.json`. P03 commands accept no unknown fields or native credential fields. Intents are bounded at 256 KiB, 100 workloads, 200 datasets, 500 dependency edges, 100 services and 100 deployment streams per application. Lists use tenant/scope-bound cursor selectors and at most 50 entries. Runtime roles cannot update or delete historical revisions, receipts, audit records or reference versions.

`002_catalogue.sql` runs under the controlled Catalogue owner. Its transaction rolls back interrupted migration and supports replay. Migration and runtime roles remain separate. A reference can retire only when no current deployment uses it; retained historical versions stay readable. Updating a reference never changes earlier intent; new publication must select current versions. Names and security-zone identity cannot be reassigned by reference updates.

Local schema/domain tests and analyzers are being run. The new P03 workflow executes production-engine PostgreSQL TLS tests, including runtime-role denials and outbox failure. Local execution cannot start PostgreSQL because the execution sandbox has no unprivileged database user; no local PostgreSQL pass is claimed. The hosted campaign is required. Actual wire/Console, concurrent-process, broker and browser qualification remains in progress.

No G03 pass, representative-user acceptance, actual managed-browser support or native qualification is claimed by this implementation increment.
