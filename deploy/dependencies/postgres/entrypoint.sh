#!/usr/bin/env bash
# Isolated P01 fixture: TLS-only TCP access and private database identities.
set -euo pipefail
umask 077

if [[ $(id -u) != 0 ]]; then
    printf '%s\n' 'PostgreSQL fixture startup requires root to prepare the TLS key.' >&2
    exit 1
fi
if [[ $# -gt 1 || ( $# -eq 1 && $1 != postgres ) ]]; then
    printf '%s\n' 'PostgreSQL fixture startup does not accept server configuration overrides.' >&2
    exit 1
fi

for secret in postgres-password postgres.crt postgres.key ca.crt; do
    if [[ ! -s /run/secrets/$secret ]]; then
        printf 'Required PostgreSQL fixture secret is missing or empty: %s\n' "$secret" >&2
        exit 1
    fi
done

# Docker Compose file-backed secrets cannot set the ownership required by PostgreSQL.
# Copy only server-side TLS material to the private ephemeral directory.
install -d -m 0750 -o postgres -g postgres /tmp/pg-tls
install -m 0600 -o postgres -g postgres /run/secrets/postgres.key /tmp/pg-tls/server.key
install -m 0644 -o postgres -g postgres /run/secrets/postgres.crt /tmp/pg-tls/server.crt
install -m 0644 -o postgres -g postgres /run/secrets/ca.crt /tmp/pg-tls/ca.crt

# The bootstrap administrator can connect only through the container's Unix socket.
# All network clients must authenticate to their own database using verified TLS.
{
    printf '%s\n' 'local all postgres peer' 'local all all reject'
    printf '%s\n' 'hostnossl all all 0.0.0.0/0 reject' 'hostnossl all all ::/0 reject'
    for service in console governance catalogue inventory planning lifecycle assurance; do
        printf 'hostssl %s %s_runtime,%s_migrator 0.0.0.0/0 scram-sha-256\n' "$service" "$service" "$service"
        printf 'hostssl %s %s_runtime,%s_migrator ::/0 scram-sha-256\n' "$service" "$service" "$service"
    done
    printf '%s\n' 'host all all 0.0.0.0/0 reject' 'host all all ::/0 reject'
} > /tmp/pg-tls/pg_hba.conf
chown postgres:postgres /tmp/pg-tls/pg_hba.conf
chmod 0600 /tmp/pg-tls/pg_hba.conf

export POSTGRES_USER=postgres POSTGRES_DB=postgres
export POSTGRES_PASSWORD_FILE=/run/secrets/postgres-password
export POSTGRES_INITDB_ARGS='--auth-local=peer --auth-host=scram-sha-256'
export POSTGRES_HOST_AUTH_METHOD=scram-sha-256
export PGDATA=/var/lib/postgresql/18/docker
unset POSTGRES_PASSWORD POSTGRES_USER_FILE POSTGRES_DB_FILE POSTGRES_INITDB_ARGS_FILE

# With umask 077, mkdir -p in the official entrypoint leaves the intermediate
# version directory root-owned and untraversable after it switches to postgres.
# Prepare the volume root and both levels explicitly; do not recursively change
# existing database data, including a volume initially created with root ownership.
install -d -m 0750 -o postgres -g postgres /var/lib/postgresql /var/lib/postgresql/18
install -d -m 0700 -o postgres -g postgres "$PGDATA"

exec /usr/local/bin/docker-entrypoint.sh postgres \
    -c listen_addresses='*' \
    -c password_encryption=scram-sha-256 \
    -c ssl=on \
    -c ssl_min_protocol_version=TLSv1.2 \
    -c ssl_cert_file=/tmp/pg-tls/server.crt \
    -c ssl_key_file=/tmp/pg-tls/server.key \
    -c ssl_ca_file=/tmp/pg-tls/ca.crt \
    -c hba_file=/tmp/pg-tls/pg_hba.conf
