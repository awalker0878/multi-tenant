# Ansible execution profiles

Local engineering and validation playbooks live under `playbooks/local`. `configuration_bundle` validates a documentation fixture and renders private JSON/CSV into a marked staging directory. `readback_validate` checks NSX, Nutanix or Neutron manifests without target contact. Both profiles fix localhost, local connection, no facts and no escalation. Native platform observers remain separately invoked and require explicit target consent.

The default inventory is `inventories/localhost.yml`. Provider credentials and remote inventories never enter ordinary PR CI. Terraform owns native resources; guest configuration has separate ownership and must not change platform policy, attachment or lifecycle fields.

## Checks

Run `python scripts/verify_ansible.py` with the pinned toolchain from `requirements-dev.txt`. It runs real engine syntax, local staging, repeat-idempotence, nonmutating check mode, rejected-input and three-platform manifest tests. Missing engines fail the gate. Engine status comes from each current report and GitHub run; source YAML parsing alone is not engine or native qualification.

See the maintained [automation process](../docs/implementation/automation/README.md) and [WSD deployment runbook](../docs/implementation/automation/wsd-deployment.md).
