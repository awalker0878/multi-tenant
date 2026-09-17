# Service identity over the worked infrastructure path

The existing fixture demonstrated routing, stateful filtering and TCP/UDP exchanges,
but port 443 alone did not establish encrypted or authenticated service access.
Increment 03 runs the original 33 observations first, replaces the data-01 challenge
listener on the same permitted port, and executes 14 additional TLS1.3 and resource
identity observations over the actual kernel-routed IPv4 path.

## What was implemented and exercised

The ephemeral service requests and validates a client certificate; clients validate
the server chain and its expected DNS name. A separately maintained fingerprint grant
limits access to the one challenge resource. A valid certificate from the same test
CA does not imply resource entitlement. To isolate this distinction, the wrong-tenant
certificate is presented **from the already network-permitted source**, and the server's
resource-denial counter is observed with a healthy authorized control.

Tests reject missing, expired and untrusted client credentials, a wrong server name,
an untrusted server root and plaintext access. The lab adds a replacement credential,
checks old/new overlap, withdraws the old resource grant, closes existing old sessions
and verifies new use is denied while the replacement session remains usable. It then
withdraws the whole entitlement and checks explicit restoration.

The result is service credential/grant withdrawal. No CRL, OCSP, enterprise federation,
KMS/HSM integration, production certificate rotation agent or universal application
authorization system is claimed. The service is a fixed bounded challenge, not an
application architecture to be deployed.

## Credential and runtime handling

Certificate/key material is freshly generated for each run in a private temporary
directory and removed afterwards. Test roots are not distributed as trusted files.
Keys are mode 0600; the containing directory is mode 0700. Client SSL contexts are
explicit so an inherited SSLKEYLOGFILE cannot export session secrets. The existing
Neutron observer received the same ambient-keylogging hardening and a regression test.
No plaintext fallback is implemented. TLS1.3 and P-256 test certificates are local
fixture choices, not a claim of government cryptographic-module validation.

The separate endpoint regression runs on 127.0.0.1 and ::1. Actual IPv6 loopback TLS
is not routed IPv6, native overlay, gateway or firewall evidence. The routed namespace
fixture remains IPv4-only; AAAA DNS data does not change that status.

## Infrastructure and operating handoff

A real service owner must accept its issuing CA, identity mapping, resource scope,
certificate lifecycle, unavailable-issuer behavior, revocation strategy and session
withdrawal timing. Network engineering supplies the permitted forward/reply path;
identity validation and resource authorization occur at the service, not at an
undifferentiated shared subnet. Qualification must use the actual service clients,
backend, installed releases, telemetry and failure model.

Source context: Python ssl verification and hostname checking, and cryptography X.509
construction interfaces; see the [primary references](../sources/increment03_references.json).
The code and tests are local implementation choices derived from the architecture's
separate service-consumption and administrative-authority requirements.
