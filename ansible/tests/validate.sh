#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
export ANSIBLE_CONFIG="$PWD/ansible/ansible.cfg"
mkdir -p build/ansible
ansible-playbook --version > build/ansible/version.txt
args=(-i ansible/inventories/ci/hosts.yml ansible/playbooks/validate.yml)
ansible-playbook "${args[@]}" --syntax-check 2>&1 | tee build/ansible/syntax.txt
ansible-playbook "${args[@]}" --check --diff 2>&1 | tee build/ansible/check-mode.txt
ansible-playbook "${args[@]}" 2>&1 | tee build/ansible/first-run.txt
sha256sum build/ansible/staging-manifest.json > build/ansible/before.sha256
ansible-playbook "${args[@]}" 2>&1 | tee build/ansible/idempotence.txt
grep -Eq 'changed=0.*unreachable=0.*failed=0' build/ansible/idempotence.txt
sha256sum --check build/ansible/before.sha256
if ansible-playbook "${args[@]}" -e hosting_allow_network_contact=true > build/ansible/rejected-native-contact.txt 2>&1; then
  echo 'ERROR: native-contact opt-in unexpectedly accepted' >&2; exit 1
fi
if ansible-playbook "${args[@]}" -e '{"hosting_domains":[{"tenant":"tenant-02","domain":"D01O","zone":"OZ","platform":"nutanix","mode":"quarantine"}]}' > build/ansible/rejected-foreign-domain.txt 2>&1; then
  echo 'ERROR: foreign domain unexpectedly accepted' >&2; exit 1
fi
printf '%s\n' '{"status":"PASSED_LOCAL_ANSIBLE_ONLY","syntax":true,"check_mode":true,"idempotence":true,"rejected_native_contact":true,"rejected_foreign_domain":true,"native_contact":false,"native_configuration_tested":false}' > build/ansible/result.json
