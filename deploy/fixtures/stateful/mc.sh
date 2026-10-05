#!/bin/sh
set -eu
umask 077
mkdir -p /tmp/mc/certs/CAs
cp /run/secrets/ca.crt /tmp/mc/certs/CAs/fixture.crt
# Keep privileged CLI streams private even when an argument is rejected. Emit only
# the step label on success and exact-secret-redacted diagnostics on failure.
run() {
 step=$1; shift
 if "$@" >/tmp/mc/step.stdout 2>/tmp/mc/step.stderr; then
  printf '%s completed\n' "$step"
 else
  code=$?
  python - "$step" "$code" <<'PY'
import json,sys
from pathlib import Path
content=Path('/tmp/mc/step.stderr').read_text(errors='replace')
for path in Path('/run/secrets').glob('*-password'):
    content=content.replace(path.read_text().strip(),'[REDACTED]')
print(json.dumps({'step':sys.argv[1],'exit_code':int(sys.argv[2]),'redacted_stderr':content}))
PY
  exit "$code"
 fi
}
run alias mc --config-dir /tmp/mc alias set local "$S3_ENDPOINT" p01root "$(cat /run/secrets/root-password)"
if [ "${1:-bootstrap}" = revoke ]; then
 run revoke mc --config-dir /tmp/mc admin user disable local assurance
 exit 0
fi
run assurance-user mc --config-dir /tmp/mc admin user add local assurance "$(cat /run/secrets/assurance-password)"
run foreign-user mc --config-dir /tmp/mc admin user add local foreign "$(cat /run/secrets/foreign-password)"
run assurance-policy mc --config-dir /tmp/mc admin policy create local assurance /fixture/assurance-policy.json
run foreign-policy mc --config-dir /tmp/mc admin policy create local foreign /fixture/foreign-policy.json
run assurance-attachment mc --config-dir /tmp/mc admin policy attach local assurance --user assurance
run foreign-attachment mc --config-dir /tmp/mc admin policy attach local foreign --user foreign
