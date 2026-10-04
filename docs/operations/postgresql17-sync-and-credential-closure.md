# Selected PostgreSQL17 sync and original credential closure

The selected application-native method uses one exact publication, logical
`pgoutput` slot and disabled subscription on separately commissioned source and
target engines. Fixed bounded reads decode whole committed source transactions.
Target row changes and their native `hosting_sync` journal entry commit together;
the original source slot advances only after that target commit is independently
observed. A lost response does not authorize applying or acknowledging again.
Schema, table/publication/subscription generations, positions, divergence and
bounded row/byte limits remain tied to the original protected selection.

Commission the source/target/fence roles, independent reader roles and immutable
helper bodies separately. The operational logins cannot read `pg_subscription`
connection secrets or alter the native journal. `connect=false`, `enabled=false`,
`create_slot=false` and `copy_data=false` ensure creation opens no subscription
connection and starts no background apply worker. PostgreSQL17 nevertheless
requires a nonempty connection password for a nonsuperuser subscription owner.
The implementation supplies a fixed public, non-authorizing metadata string:

```text
hostaddr=127.0.0.1 port=1 dbname=hosting_disabled_subscription user=hosting_disabled_subscription password=hosting_disabled_subscription sslmode=verify-full sslrootcert=/dev/null passfile=/dev/null connect_timeout=1
```

This contains no Vault/source credential. Its empty TLS trust file and pinned
loopback endpoint cannot authenticate to the selected source. The commissioned
`inspect_subscription` helper returns only whether the connection equals those
exact bytes, plus the fixed nonsecret metadata. Any connection change, enabling,
skip, background worker or original generation replacement holds further work.
Do not enable this subscription or replace the public marker with a real secret.

Current writer exclusion considers login roles that can `SET ROLE` to a table
writer, including existing sessions after `NOLOGIN`. Restricted statistics can
hide a session's backend type; hidden writer details remain uncertainty rather
than exclusion. Fence the original writers, terminate their sessions and retain
separate independent native exclusion before source return or target admission.

B10 credential custody is append-only. Migration 0036 grants the trusted tenant
runtime a scoped `lock_native_credential_grant` function rather than table UPDATE
permission. Under `READ COMMITTED`, issuance and retirement lock the original
grant and recheck its durable closure. SQL append triggers enforce the same
serialization for direct inserts. Immutable custody reads and irreversible
worker/certificate revocations need no mutation privilege to be observed.
Migration 0037 keeps closure immutability inside `hosting_controlplane`, so a
control-plane-only backup restores without depending on the separately
commissioned native `hosting_sync` schema.

Close the actual original SQL connections before retirement. Record durable
closure before synchronously revoking every exact original Vault lease, then
independently recontact the native/Vault owners. Unknown issuance, a missing
consumed lease, lost revocation, live writer or unavailable independent reader
holds the original intent and resources. Expiry is not proof of exclusion.

Disposable PostgreSQL17 tests verify actual journal atomicity, slot/publication
operations, disabled metadata, read-role restrictions, writer delegation and
concurrent closure. Loopback Vault tests use synthetic backend responses. Neither
suite qualifies a production Vault plugin, site tuple or migration method. Run
the final native database and application campaigns before advertising support.

Primary contracts: [CREATE SUBSCRIPTION](https://www.postgresql.org/docs/17/sql-createsubscription.html),
[statistics visibility](https://www.postgresql.org/docs/17/monitoring-stats.html),
and [subscription catalog](https://www.postgresql.org/docs/17/catalog-pg-subscription.html).
