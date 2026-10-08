# Console operator readiness and theme

The user requested required operator inputs, clearer terminology, a professional
console theme and merge to main. This implementation supplies the missing
collection surface for selected P07/P08/P10 commissioning inputs. It does not
record a new architecture decision or an accountable operating acceptance.

## Operator workflow

1. Open a site in **Observed inventory**. Use **Environment configuration** to
   enroll/pull the native configuration and review the API findings.
2. Open **Operator readiness** and complete the five owner-labelled sections.
   Enter only protected record identifiers for the underlying owner records.
3. Save a partial draft at any time. The checklist identifies each missing input;
   zero is valid for maximum outage and data loss.
4. Review the current environment configuration after it changes and save a new
   operator-input revision bound to its digest.
5. Download the saved packet for the commissioning/qualification team. Obtain
   original evidence and independent acceptance through the existing native
   qualification and P10 dossier procedures.

| Section | Inputs collected | Work it enables |
| --- | --- | --- |
| Accounts and trust | Six execution/verification secret references, account scope, TLS/rotation | Commission actual source, destination and image-transfer identities |
| Execution and verification | Independent custody, stale-worker exclusion, reservations, guest recipe, shared services, measurements | Bind and qualify concrete native owner protocols |
| Application recovery and cutover | Consistency, delta/cold method, writer isolation, traffic/policy, restore, recovery and retention | Prepare Q05–Q07 native campaigns and both data recovery boundaries |
| Operating targets | Approved objective record, outage seconds, data-loss bytes, recovery seconds, maximum active migrations | Supply representative workload and capacity objectives for P08/P10 |
| Service handover | Campaign authority, installed artifacts, security findings, alert routing, receiving team and support rehearsal | Assemble actual operating and receiving inputs for P10 |

The site packet describes the representative commissioning scope. Individual
workload datasets/objectives and migration schedules stay in their existing
VM review and campaign forms. The packet does not automatically rewrite
`release/p07-native-inputs.json` or `release/p10-inputs.json`: those require original
observations, exact candidate/tuple binding and independent receiving decisions.
Nor does it mount secrets, enroll endpoint policy, configure native workers,
mark references verified, or remove operational admission holds. These actions
remain explicit commissioning steps owned by the responsible services.

## Persistence and deployment

Apply `services/inventory/migrations/007_operator_inputs.sql` using the existing
Inventory migration owner before deploying this console/service increment. The
runtime role has SELECT/INSERT only on the new immutable revision table. Saves
require site-scoped `inventory.admin`, use existing delegated actor credentials,
CSRF protection, revision preconditions and idempotency receipts. Audit events
record the revision and digest without the input values.

Inventory contract 1.4 adds GET/POST operator-input operations and preserves every
published 1.3 schema and path. Its generated Console/Python clients remain checked.
Raw native facts cannot be supplied through these fields. Packet export performs
a fresh authorization check and sets no-store headers. All records and exports
retain `native_write_authorized: false`. Distinct reference strings are checked;
actual independent account permissions still require native commissioning.

## Verification

The change adds domain/database checks for draft persistence, zero-valued targets,
invalid references, independent accounts, tenant/site isolation, stale writes,
idempotent replay, immutable history and changed configuration binding. Console
HTTP tests exercise zero forwarding, CSRF, encrypted history, access rechecks,
export and stale/uncertain failures. The browser journey covers real Vue/Inertia
form interactions, unchanged retries, preserved edits, mobile navigation/reflow
and revoked access; its HTTP owner is a synthetic fixture. Exact-source hosted
checks provide the PHP/PostgreSQL and pinned browser evidence before merge.

The shared theme applies to the catalogue/inventory/planning/jobs shell and
identity pages. It introduces a consistent brand mark, navy navigation, teal
actions, reusable colour/spacing tokens and accessible status labels.

Collection gaps are addressed in software; BL-P07-001, BL-P08-001/002 and
BL-P10-001/002 remain open wherever actual native evidence, owner implementation
or receiving decisions are still absent.
