#!/usr/bin/env bash
set -euo pipefail
umask 077
[[ $(id -u) == 0 && $# == 0 ]] || exit 1
install -d -m 0750 -o postgres -g postgres /tmp/pg-tls /var/lib/postgresql /var/lib/postgresql/18
install -d -m 0700 -o postgres -g postgres /var/lib/postgresql/18/docker
install -m 0600 -o postgres -g postgres /run/secrets/postgres.key /tmp/pg-tls/server.key
install -m 0644 -o postgres -g postgres /run/secrets/postgres.crt /tmp/pg-tls/server.crt
cat > /tmp/pg-tls/pg_hba.conf <<'HBA'
local all postgres peer
local all all reject
hostnossl all all 0.0.0.0/0 reject
hostssl permit_desk pd_runtime,pd_migrator,pd_backup 0.0.0.0/0 scram-sha-256
host all all 0.0.0.0/0 reject
host all all ::/0 reject
HBA
chown postgres:postgres /tmp/pg-tls/pg_hba.conf
export POSTGRES_PASSWORD_FILE=/run/secrets/postgres-password POSTGRES_DB=postgres POSTGRES_USER=postgres
export POSTGRES_INITDB_ARGS='--auth-local=peer --auth-host=scram-sha-256'
export PGDATA=/var/lib/postgresql/18/docker
exec /usr/local/bin/docker-entrypoint.sh postgres -c listen_addresses='*' \
 -c ssl=on -c ssl_min_protocol_version=TLSv1.2 -c ssl_cert_file=/tmp/pg-tls/server.crt \
 -c ssl_key_file=/tmp/pg-tls/server.key -c hba_file=/tmp/pg-tls/pg_hba.conf \
 -c password_encryption=scram-sha-256
