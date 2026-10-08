#!/usr/bin/env bash
set -euo pipefail
umask 077
for name in temporal visibility; do
 export FIXTURE_RUNTIME_PASSWORD="$(cat /run/secrets/$name-runtime-password)"
 export FIXTURE_MIGRATOR_PASSWORD="$(cat /run/secrets/$name-migrator-password)"
 db=temporal; [[ $name == temporal ]] || db=temporal_visibility
 psql -X -q -v ON_ERROR_STOP=1 --username postgres --dbname postgres -v db="$db" -v runtime="${name}_runtime" -v migrator="${name}_migrator" <<'SQL'
\set ECHO none
\getenv runtime_password FIXTURE_RUNTIME_PASSWORD
\getenv migrator_password FIXTURE_MIGRATOR_PASSWORD
SET log_statement='none';
SET log_min_error_statement='panic';
CREATE ROLE :"runtime" LOGIN NOINHERIT PASSWORD :'runtime_password';
CREATE ROLE :"migrator" LOGIN NOINHERIT PASSWORD :'migrator_password';
CREATE DATABASE :"db" OWNER :"migrator" TEMPLATE template0;
REVOKE ALL ON DATABASE :"db" FROM PUBLIC;
GRANT CONNECT ON DATABASE :"db" TO :"runtime";
SQL
 psql -X -q -v ON_ERROR_STOP=1 --username postgres --dbname "$db" -v runtime="${name}_runtime" -v migrator="${name}_migrator" <<'SQL'
REVOKE ALL ON SCHEMA public FROM PUBLIC;
GRANT USAGE ON SCHEMA public TO :"runtime";
ALTER DEFAULT PRIVILEGES FOR ROLE :"migrator" IN SCHEMA public GRANT SELECT,INSERT,UPDATE,DELETE ON TABLES TO :"runtime";
ALTER DEFAULT PRIVILEGES FOR ROLE :"migrator" IN SCHEMA public GRANT USAGE,SELECT ON SEQUENCES TO :"runtime";
ALTER DEFAULT PRIVILEGES FOR ROLE :"migrator" REVOKE EXECUTE ON ROUTINES FROM PUBLIC;
SQL
done
