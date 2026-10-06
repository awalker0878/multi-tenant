# P02 independent recovery custody

Owner: Governance/IAM and the independent recovery custodian. Packages
P02.01/P02.03/P02.04; criteria G02.01/G02.03/G02.04. The user authorized secure
custody and resumption implementation on 2026-10-05. This is development authority,
not an assignment of operating people, keys, hosts or an actual restore approval.

## Database foundation

Migration 011 removes runtime permission to change an established identity-admission
binding. Its narrow owner-defined bootstrap function can initialize only a null
binding while the bootstrap sentinel is still uninitialized. It uses fully qualified
tables, a fixed safe search path, no dynamic SQL and no public execution permission.
The existing randomized bootstrap/forced-change/irreversible-retirement behavior
remains authoritative.

Recovery receipts and separate release authorizations belong to the migration
owner. Runtime can read them but cannot insert, update or delete them. A recovery
binding cannot admit requests without its separate release record, even when an
external descriptor is accidentally made active early. Normal startup and HTTP
routes cannot rebind a restored installation.

## Custodian and owner ceremony

The [custody tool](../../scripts/recovery/custody.py) enrolls verified external public
keys, holds/rotates admission, validates two independent RSA signatures and appends
an fsynced hash-linked journal before releasing a held generation. Private keys stay
encrypted on the separate signing workstations. The custodian has no application
or database credential; runtime has no custody write/signing or owner credential.

The owner-only `identity:recovery` command prepares a 15-minute exact-state plan,
applies its two signatures while held, prepares a distinct post-reconciliation
release plan and confirms that second two-person authorization. Code, all owned
table contents, external generation, signer policy, provider configuration/current
keys and rotated workload credentials are rechecked. Old sessions/delegations,
grants/approvals/support authority are revoked. Existing memberships survive only
when expressly selected against current owner records; other tenants stay suspended.
No local bootstrap reset, automatic rebind, API recovery endpoint or native permit
is introduced. Current OIDC settings remain Console-managed application data.

The [operator procedure](../operations/runbooks/identity-recovery-custody.md) defines
all inputs, commands, review boundaries, failure containment and key/restore limits.
Local feature and custody tests cover the mechanism. The hosted campaign additionally
executes real PostgreSQL roles, encrypted-key terminal signing, the separate custodian
process, full-schema recovery and fresh HTTPS OIDC sign-in. Record results only after
that exact-source campaign passes. Actual OP03/OP05/OP06 operators, key-service and
host/mount/backup separation remain required operating evidence; G02 is not inferred.
