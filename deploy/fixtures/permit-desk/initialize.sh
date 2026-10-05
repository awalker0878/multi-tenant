#!/usr/bin/env bash
set -euo pipefail
umask 077
export PD_RUNTIME_PASSWORD="$(cat /run/secrets/runtime-password)"
export PD_MIGRATOR_PASSWORD="$(cat /run/secrets/migrator-password)"
export PD_BACKUP_PASSWORD="$(cat /run/secrets/backup-password)"
psql -X -q -v ON_ERROR_STOP=1 --username postgres --dbname postgres <<'SQL'
\set ECHO none
\getenv runtime_password PD_RUNTIME_PASSWORD
\getenv migrator_password PD_MIGRATOR_PASSWORD
\getenv backup_password PD_BACKUP_PASSWORD
SET log_statement='none';
SET log_min_error_statement='panic';
CREATE ROLE pd_owner NOLOGIN;
CREATE ROLE pd_runtime LOGIN NOINHERIT PASSWORD :'runtime_password';
CREATE ROLE pd_migrator LOGIN NOINHERIT PASSWORD :'migrator_password';
CREATE ROLE pd_backup LOGIN NOINHERIT PASSWORD :'backup_password';
GRANT pd_owner TO pd_migrator WITH INHERIT FALSE, SET TRUE;
CREATE DATABASE permit_desk OWNER pd_owner TEMPLATE template0;
REVOKE ALL ON DATABASE permit_desk FROM PUBLIC;
GRANT CONNECT ON DATABASE permit_desk TO pd_runtime,pd_migrator,pd_backup;
SQL
psql -X -q -v ON_ERROR_STOP=1 --username postgres --dbname permit_desk <<'SQL'
REVOKE ALL ON SCHEMA public FROM PUBLIC;
ALTER DEFAULT PRIVILEGES FOR ROLE pd_owner REVOKE EXECUTE ON ROUTINES FROM PUBLIC;
SQL
