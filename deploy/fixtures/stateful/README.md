# Disposable stateful dependencies

P01.02/P01.05/P01.06 support fixture, owned by SRE with Lifecycle and Assurance.
Run `python scripts/p01/run_stateful.py --source-revision <full-commit> --output <outside-source-path>`
from a clean checkout with Docker and Compose. The output directory must not exist.
The runner builds exact client and source-based object-store images, creates a private
runtime directory, installs empty volumes and removes its own containers, networks,
volumes and credentials on successful cleanup. Never use production credentials.

The renderer publishes no host ports. Client probes run on separate internal networks.
RabbitMQ exposes verified TLS with scoped publish/consume/vhost credentials. Temporal
uses TLS, an explicit JWT authorizer and a Lifecycle namespace, plus private PostgreSQL
runtime roles. Schema tooling runs separately; migrators are disabled after bootstrap.
Internal Temporal services bind loopback inside the single server container.

Two separately credentialed S3 stores exercise retained object versions and a real
restore into empty storage. Prefix-scoped runtime credentials cannot administer users,
list buckets or delete versions. COMPLIANCE retention is also challenged with the
bootstrap administrator. New object versions never replace the recorded evidence
version/digest pair. Restore creates a new version and records the original identity
as metadata. It does not preserve the source store's native version identifier.

The fixture is not a product event adapter, production dependency adoption or G01
acceptance. Product outbox/inbox, shared Console sessions/cache, external issuer
integration, alert receipt, HA and retention authority remain separate work.
See [the implementation record](../../../docs/implementation/p01-stateful-dependencies.md).
