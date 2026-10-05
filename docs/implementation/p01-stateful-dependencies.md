# P01 stateful dependency integration

P01.05, with receiving P01.02/P01.03/P01.06 work. Owners: SRE and the Catalogue,
Planning, Lifecycle and Assurance service owners. Requirements R02/R15/R29/R35;
criteria G01.02/G01.03/G01.05/G01.06. The approved development baseline already
selects RabbitMQ and Temporal. These experiments select exact disposable inputs;
operated adoption and gate acceptance remain separate.

## Candidate inputs and source basis

Checked 2026-10-05 against primary sources:

| Dependency | Development candidate and basis |
| --- | --- |
| RabbitMQ | [4.3.6](https://www.rabbitmq.com/release-information), selected event transport; verified TLS, imported users/vhosts and explicit queue/exchange permissions |
| Temporal | [1.32.0](https://github.com/temporalio/temporal/releases/tag/v1.32.0), using separate supported server and admin-tools images; explicit private PostgreSQL schema setup and restricted runtime credentials |
| Evidence storage | MinIO [security-fixed source release](https://github.com/minio/minio/releases/tag/RELEASE.2025-10-15T17-29-55Z), commit `9e49d5e7a648f00e26f2246f4dc28e6b07f8c84a`; build from source because this release directs container users to build it rather than consume an older prebuilt image |
| Build tool | Go [1.27.1](https://go.dev/doc/devel/release#go1.27.1); fixed image manifest and source archive hashes must be observed before the replay |
| Clients | Pika 1.4.4, Temporal Python 1.34.0, Boto3 1.43.108, PyJWT 2.15.1, Psycopg 3.3.6 and JSON Schema 4.26.0; exact transitive wheel hashes are observed into a private integration-driver lock |

The source-built object store is a disposable S3 behavior fixture. It does not select
a production vendor, support service, security certification, key custodian or
retention authority. Its AGPL source and exact source/build closure remain explicit.
Product dependencies do not import this integration-driver environment.

The [candidate inventory](../../deploy/dependencies/stateful/candidates.json) and
[observation workflow](../../.github/workflows/p01-stateful-inputs.yml) collect actual
platform manifests, a source-archive checksum and client closure. Candidate names
are not immutable locks or successful installation evidence. Record actual results
here and in the delivery register only after execution.

Required controls follow RabbitMQ's [TLS](https://www.rabbitmq.com/docs/ssl),
[access controls](https://www.rabbitmq.com/docs/access-control) and
[definition import](https://www.rabbitmq.com/docs/definitions) interfaces. Temporal's
[service configuration](https://docs.temporal.io/references/service-configuration)
distinguishes TLS client authentication from its JWT claim mapper and authorizer;
a client certificate alone does not establish namespace authorization. The deployment
must explicitly enable the authorizer and exercise wrong-namespace/invalid identity
cases. Private synthetic trust material is not operated issuer integration.

## Session and cache inventory

The measured Console foundation uses a file session driver inside a disposable
single replica. This is not shared-session readiness. The selected implementation
path is service-owned PostgreSQL session/cache tables, using the existing private
Console database and restricted runtime role; a separate Redis/Valkey deployment is
not required by the accepted architecture. Implement and measure shared-session
persistence and isolation before claiming that P01 dependency requirement complete.
Authentication/session revocation semantics remain P02 obligations.

## Input discovery correction

Run [37250318779](https://github.com/awalker0878/multi-tenant/actions/runs/37250318779)
failed before installation: the proposed Temporal auto-setup 1.32.0 image does not
exist. The upstream docker-builds project deprecates auto-setup. The corrected
candidates use the supported server/admin-tools images separately. This failure is
not an installation or authorization pass. Resolver commands now retain both output
streams and exit status, including failed commands.
