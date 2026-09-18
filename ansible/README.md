# Ansible — separate local engineering and verification responsibilities

Increment 04 contained no Ansible source. These are **new candidate playbooks**,
not imported or already-qualified vendor installers.

`configuration_bundle` validates an explicit documentation-only engineering fixture,
requires a caller-created marked staging directory, and renders a private JSON
handoff and CSV route schedule. It does not configure Linux routing, a switch,
firewall, hypervisor or service. Staging requires a Boolean opt-in; templates never
grant apply or activation authority. This is the local P4 engineering handoff, not
a new tenant provisioning API.

`readback_validate` runs the existing NSX/Nutanix validation-only CLI against an exact
manifest and verifies `INPUT_VALID_NO_CONTACT`. The playbook has no native-contact
option. Use separately accepted native readback procedures outside automatic CI.

Both playbooks fix localhost, local connection, no facts and no escalation. No
remote inventory, SSH credential, package installation, service restart or native
mutation is included. Terraform and Ansible therefore have no competing native
resource owner in this release.

## Tests

From the repository root, run `python scripts/verify_ansible.py`. With the actual
Ansible engine installed it performs syntax checking, renders in a temporary marked
workspace, repeats to require zero changes, checks drift in check mode without
mutating files, exercises invalid/unapproved inputs and runs both manifest-validation
variants. Workspaces are removed afterwards. Missing engines produce BLOCKED status
and nonzero exit; Python/Jinja source tests are separately identified.

The authoring runtime could not install Ansible. **Engine syntax, check-mode and
idempotence tests are authored but not run here.** CI performs the real gate after
push; static YAML parsing is not claimed as engine validation.
