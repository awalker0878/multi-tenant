#!/usr/bin/env bash
# Mount as /docker-entrypoint-initdb.d/10-private-identities.sh (read-only).
# The official image invokes this as postgres only for an empty PGDATA directory.
set -euo pipefail
umask 077

for service in console governance catalogue inventory planning lifecycle assurance; do
    for identity in runtime migrator; do
        if [[ ! -s /run/secrets/$service-$identity-password ]]; then
            printf 'Required database identity secret is missing or empty: %s-%s-password\n' "$service" "$identity" >&2
            exit 1
        fi
    done
done

for service in console governance catalogue inventory planning lifecycle assurance; do
    # psql reads passwords from its environment, never argv, SQL files or output.
    # Its literal-variable expansion quotes password values as SQL string literals.
    export FOUNDATION_RUNTIME_PASSWORD="$(cat "/run/secrets/$service-runtime-password")"
    export FOUNDATION_MIGRATOR_PASSWORD="$(cat "/run/secrets/$service-migrator-password")"
    if [[ -z $FOUNDATION_RUNTIME_PASSWORD || -z $FOUNDATION_MIGRATOR_PASSWORD ]]; then
        printf 'Required database identity secret contains no password: %s\n' "$service" >&2
        exit 1
    fi

    psql -X --quiet --username=postgres --dbname=postgres \
        --set=ON_ERROR_STOP=1 --set="database=$service" \
        --set="owner=${service}_owner" --set="runtime=${service}_runtime" \
        --set="migrator=${service}_migrator" <<'SQL'
\set ECHO none
\set VERBOSITY terse
\getenv runtime_password FOUNDATION_RUNTIME_PASSWORD
\getenv migrator_password FOUNDATION_MIGRATOR_PASSWORD
SET log_statement = 'none';
SET log_min_error_statement = 'panic';
CREATE ROLE :"owner" NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
CREATE ROLE :"runtime" LOGIN NOINHERIT NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS PASSWORD :'runtime_password';
CREATE ROLE :"migrator" LOGIN NOINHERIT NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS PASSWORD :'migrator_password';
GRANT :"owner" TO :"migrator" WITH INHERIT FALSE, SET TRUE;
CREATE DATABASE :"database" OWNER :"owner" TEMPLATE template0;
REVOKE ALL ON DATABASE :"database" FROM PUBLIC;
GRANT CONNECT ON DATABASE :"database" TO :"runtime", :"migrator";
ALTER ROLE :"runtime" IN DATABASE :"database" SET search_path = pg_catalog, app;
ALTER ROLE :"migrator" IN DATABASE :"database" SET search_path = pg_catalog, app;
SQL
    unset FOUNDATION_RUNTIME_PASSWORD FOUNDATION_MIGRATOR_PASSWORD

    psql -X --quiet --username=postgres --dbname="$service" \
        --set=ON_ERROR_STOP=1 --set="owner=${service}_owner" \
        --set="runtime=${service}_runtime" <<'SQL'
\set ECHO none
\set VERBOSITY terse
BEGIN;
REVOKE ALL ON SCHEMA public FROM PUBLIC;
CREATE SCHEMA app AUTHORIZATION :"owner";
GRANT USAGE ON SCHEMA app TO :"runtime";
ALTER DEFAULT PRIVILEGES FOR ROLE :"owner" IN SCHEMA app GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO :"runtime";
ALTER DEFAULT PRIVILEGES FOR ROLE :"owner" IN SCHEMA app GRANT USAGE ON SEQUENCES TO :"runtime";
ALTER DEFAULT PRIVILEGES FOR ROLE :"owner" REVOKE EXECUTE ON ROUTINES FROM PUBLIC;
COMMIT;
SQL
    printf 'Bootstrapped private database and identities: %s\n' "$service"
done

# No application tables are created as administrator. The installation runner must
# apply migrate.sql using each authenticated migrator over TLS before readiness.
