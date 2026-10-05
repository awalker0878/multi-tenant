#!/bin/sh
set -eu
export SQL_HOST=postgres SQL_PORT=5432 SQL_PLUGIN=postgres12 SQL_TLS=true
export SQL_TLS_CA_FILE=/run/secrets/ca.crt SQL_TLS_SERVER_NAME=postgres
for name in temporal visibility; do
 export SQL_USER="${name}_migrator"
 export SQL_PASSWORD="$(cat /run/secrets/$name-migrator-password)"
 export SQL_DATABASE=temporal
 [ "$name" = temporal ] || export SQL_DATABASE=temporal_visibility
 temporal-sql-tool setup-schema -v 0.0
 temporal-sql-tool update-schema --schema-name "postgresql/v12/$name"
done
