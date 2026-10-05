# P02 tenant and membership directories

Owner: Governance/IAM and Console. Packages P02.02/P02.03/P02.05;
requirements R03/R04; criteria G02.01/G02.03/G02.04; campaign Q01.

## Current behavior

The Console tenant selector and membership administration use the new
[Governance directory contract](../../contracts/openapi/governance-directory-v1.json).
Each response returns at most 50 rows and an opaque `next_cursor`, or null at the
end. First-page and next-page links expose all current entries beyond the former
200-row limit. A membership-page change explicitly warns that unsaved edits will
be discarded. Invalid or expired page links restart at the first page with a
notice; owner outages remain errors rather than empty successful lists.

Governance orders by immutable UUID and advances by the last returned ID. Equal
names do not collapse entries. This is a live listing, not a snapshot or an export:
entries inserted before a prior cursor require restarting the list; authorization
changes take effect on the next request. No totals for inaccessible records are
returned. Suspended tenants remain listed for their authorized members, as in the
existing account journey; only a currently authorized administrator can reactivate.

Each continuation is authenticated and encrypted with the Governance application
key and binds the user session, internal actor and directory scope. It expires
after 15 minutes, or becomes unusable earlier when the session/authority ends.
Every request resolves current workload and user identity before using a position;
membership pages also recheck unscoped membership-management permission. A cursor
cannot confer membership or bypass revoked, expired or site-scoped authority.
Cursor values contain no usable credential and are not an authorization cache.
Keep the existing no-store response and history-clearing behavior.

The Console forwards only the approved, encoded cursor query. Browser actor,
tenant, role, page size and offset fields do not alter owner scope. Changing to a
different tenant discards that tenant's cursor and page state. Notification hints
continue to use the independently authorized owner read; directory positions have
no event, quota-revision or freshness meaning.

## Install and compatibility

Apply Governance migrations 001–008 with its migrator before enabling this
increment. Migration 008 adds tenant/position and actor/position indexes without
rewriting rows or widening runtime privileges. Existing migration discovery applies
it in the P02 hosted campaign. Index creation takes normal PostgreSQL index-build
locks; schedule the migration for an approved maintenance window on a populated
installation. No production duration or capacity claim is made.

The published tenancy v1 contract and endpoints keep their existing bounded
responses. The new endpoints are `/v1/tenant-directory` and
`/v1/tenants/{tenant}/membership-directory`; no existing schema bytes change.
Deploy the Governance owner first, then the Console. An old owner lacking the new
endpoints is an incompatible deployment and is not silently used as a truncated
fallback. Grant/audit v1 lists remain bounded and are not yet paged Console views.

## Verification and limits

The local directory cases traverse 206 tenants and 206 memberships, exercise
duplicate names, scope/session substitution, tampering, expiry, role changes and
revocation, and confirm the original v1 bound remains unchanged. Console cases
verify forwarding, current authorization, page props, malformed-link recovery,
unavailable owners and cross-tenant denial. The hosted campaign includes these
cases on PostgreSQL plus the existing compiled three-engine journey.

Each execution needs its own source-bound evidence; new test implementation is
not a hosted pass. Managed-browser floor, manual assistive technology, full
restore/revocation reconciliation, exceptional-access policy and independent
G02 acceptance remain open. The new contract does not change these conditions.
