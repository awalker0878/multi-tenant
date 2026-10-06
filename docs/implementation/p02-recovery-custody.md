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
Actual OP03/OP05/OP06 operators, key-service and host/mount/backup separation remain
required operating evidence; G02 is not inferred.

## Qualified source and retained evidence

Source `7ec7a60623f60c84ba3356978f0ff51b03e9ca7e` passes the final local and
hosted recovery campaigns. [EV-P02-023/024](delivery-register.yaml) register the
original [qualification index](../../verification/p02/recovery-custody/qualification-index.json),
retained at commit `646b615b7137bfab300c129bc3baa71ad9972b3b`.

| Evidence | Measured result |
| --- | --- |
| Local Governance/custody | 239 Governance cases / 5,564 assertions, including 28 recovery cases; PHPStan, Deptrac and Pint pass. Eleven real encrypted-key custody tests cover positive, negative and crash paths. Five commands, ten log hashes and 218 source bindings match. Twelve PostgreSQL/TLS cases are explicitly skipped locally. |
| Three hosted identity campaigns | Chromium, Firefox and WebKit each pass 156 checks, 205 Governance PostgreSQL cases / 5,471 assertions, 66 Console PostgreSQL/TLS cases / 248 assertions and both compiled browser journeys with no skips, retries or failures. Each original archive matches 358 source bindings and 25 artifact hashes. |
| Actual disposable recovery ceremony | Owner role and runtime denials, separate custody process, two encrypted-key terminal signatures, rejected single approval, committed held reconciliation, early descriptor-opening denial, second signed authorization, full-schema receipt/release restore, independent release and fresh HTTPS OIDC sign-in. A later hold defeats the restored previously confirmed database. |
| Event regression | 74 PostgreSQL/TLS event cases / 1,358 assertions; 217 source bindings and ten log hashes match, including durable support event delivery and queue isolation. |

The [final regression receipt](../../verification/p02/recovery-custody/hosted-final.json)
records all nine workflows passing at Governance/runtime source `7ec7a60`, including independent packages,
images, contracts, policy, events, Compose and Kubernetes. All selected jobs pass;
the unchanged Python application-package family is explicitly unselected.

The [corrections record](../../verification/p02/corrections.md) preserves the initial
wrong-schema observation and an earlier empty Kubernetes helper response. No failure
is relabelled and no published contract, mandatory assertion or security gate is
weakened. A full environment co-rollback remains outside this filesystem mechanism;
actual independent people/keys/hosts, current owner records and receiving approval
must come from the operating owners, never synthetic fixture identities.


## Protected terminal refinement

Source `d5ccd142cca22e51448a1a86996bbd0a14cba2b5` refuses signing without an
interactive terminal or when Python cannot protect terminal echo. It never falls
back to visible passphrase input. [EV-P02-025](delivery-register.yaml) retains
[the final qualification](../../verification/p02/recovery-custody/terminal-hardening/qualification-index.json):
13 custody cases pass locally and in every repeated 156-check Chromium, Firefox
and WebKit campaign. The real encrypted-key terminal ceremony remains successful.
All 358 source bindings and 25 artifact hashes per engine match.

The index records identical Git tree identities for every unchanged application,
deployment, P01/P02 integration, contract and workflow directory. The 239-case
Governance local suite, 74-case event campaign and complete nine-workflow runtime
regression at `7ec7a60` therefore remain the evidence for those unchanged components.
The earlier reports retain their original sources and 11-case custody counts.
