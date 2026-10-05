#!/bin/sh
set -eu
umask 077
mkdir -p /tmp/mc/certs/CAs
cp /run/secrets/ca.crt /tmp/mc/certs/CAs/fixture.crt
mc --config-dir /tmp/mc alias set local "$S3_ENDPOINT" p01root "$(cat /run/secrets/root-password)" >/dev/null
if [ "${1:-bootstrap}" = revoke ]; then
 exec mc --config-dir /tmp/mc admin user disable local assurance
fi
mc --config-dir /tmp/mc admin user add local assurance "$(cat /run/secrets/assurance-password)"
mc --config-dir /tmp/mc admin user add local foreign "$(cat /run/secrets/foreign-password)"
mc --config-dir /tmp/mc admin policy create local assurance /fixture/assurance-policy.json
mc --config-dir /tmp/mc admin policy create local foreign /fixture/foreign-policy.json
mc --config-dir /tmp/mc admin policy attach local assurance --user assurance
mc --config-dir /tmp/mc admin policy attach local foreign --user foreign
