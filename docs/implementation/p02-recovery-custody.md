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

The remaining implementation supplies the independent signer/custodian ceremony,
exact-state reconciliation, controlled resumption, operating procedure and hosted
qualification. Actual OP03/OP05/OP06 custody and G02 receiving remain open until
their specific operating evidence and decisions exist.
