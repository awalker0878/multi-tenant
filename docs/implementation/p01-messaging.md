# P01 transactional messaging foundation

Owner: Catalogue producer and Planning consumer. Packages P01.03/P01.05/P01.06;
requirements R02/R15/R35. This increment implements an internal reference fact,
`catalogue.foundation.recorded` version 1. It does not add a Catalogue intent API,
assessment, execution command, grant or native effect. G01 remains open.

The authoritative JSON Schema and AsyncAPI channel live under `contracts/`.
`generate.py` copies the schema into each independently built service and generates
private scalar DTOs. Opis 2.6.0 and Python jsonschema 4.26.0 validate wire data before
decoding; Python also checks the exact UTC calendar value. Unsupported versions,
unknown fields, missing actor, malformed digest and numeric revisions fail. IDs
and digests use bounded ASCII fields; revisions are decimal strings preserving
values beyond JavaScript's exact integer range. Canonical envelope bytes sort the
fixed scalar keys and omit whitespace. This is envelope canonicalization only,
not a plan or business-command canonicalization algorithm.

Catalogue's internal `RecordFoundationFact` accepts trusted tenant/actor context
from its caller and rejects a different event binding or payload digest. The P01
campaign supplies synthetic context; no authenticated public endpoint is exposed.
Its private transaction writes the immutable fact and outbox together. Event IDs
bind to the exact canonical envelope. An identical retry returns `duplicate`;
changed content conflicts. A one-row `FOR UPDATE SKIP LOCKED` transaction is the
relay claim. Broker publish uses TLS, mandatory routing, durable publication and
publisher confirms; only then is the outbox marked published. A failed connection
or crash releases the database lock and leaves the same event available.

Planning validates the dedicated producer route, broker-verified `user_id`, schema
and current consumer tenant scope. Inbox identity/digest and the local projection
commit together. A duplicate has no second effect; changed content under an ID
is rejected. Tenant/record head locks require the next revision. Gaps and stale
unseen events are quarantined for owner reconciliation. The quorum queue bounds
transient redelivery to five; malformed/denied messages go directly to the private
quarantine queue. Neither receipt nor replay changes user or native authority.

The inbox requires an idle autocommit connection before it starts its owned
transaction. An outer transaction is rejected before decoding or SQL: a savepoint
must never let the consumer acknowledge an event before the durable commit.

No automatic pruning is implemented: facts, inbox and outbox share their service's
backup/recovery group. Production receipt-retention and replay windows remain an
operating input. Consumer databases contain reference/digest projections only.
No cross-service SQL access or credentials are shared by runtime clients.

## Verification

The local PHP/Python conformance check covers 16 shared fixtures and compares exact
canonical hashes for accepted events. PHP static and architecture analysis and
Python static analysis have been exercised locally. EV-P01-015 retains hosted run
`37260022743` at `471b3d07fc5f0043de8827f280d25fd1b1df5ec1`: all 35 real-dependency
checks and all 16 shared fixtures pass. Examination verified 186 command-log hashes
and 74 immutable source bindings across the campaign and its two image builds.
The Planning package run at that same source also passed the two outer-transaction
guard cases. These observations are not a G01 pass. The separate
[HTTP increment](p01-http-contracts.md) adds diagnostic clients and conservative
version freezing; protected admission and other service event integrations remain
distinct P01/P02+ work.

The hosted campaign is `scripts/p01/run_messaging.py`: it builds only the two owned
images, installs TLS dependencies without host ports, runs the owner migrations,
and injects denied outbox/projection writes, producer/consumer process loss,
broker/database restart, tenant denial, sequence gaps, outage and publisher
revocation. It retains source/image identities, results and cleanup; a definition
of a check is not evidence of its execution.

Initial hosted run `37258199569` passed conformance but stopped before image build:
the image verifier's explicit Catalogue input list had not yet admitted its owned
contract resources. The follow-up adds that exact directory, retaining the strict
input allowlist. The nine-package run `37258199557` passed on the preceding source.

The first admitted Catalogue image then exposed a missing runtime extension:
php-amqplib requires `ext-sockets`, present on the package-test host but absent in
the minimal FPM image. Catalogue now compiles sockets alongside PDO PostgreSQL;
Composer platform verification remains enabled. Failed image artifact `11323877080`
from run `37258781431` retains the exact dependency error.

The [retained report](../../verification/p01/messaging/run-37260022743/retrieval.json)
contains actual outcomes for every injected fault. Fact/outbox and inbox/projection
failures roll back together; crash/restart and uncertain publication deliver one
logical projection. Tenant/actor/identity binding, revision gaps and revoked
publication fail as specified. Broker recovery resumes pending work and cleanup
removes every generated container, volume and network.
