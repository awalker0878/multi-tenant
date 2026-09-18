# Terraform — provider-native owned scopes

Ten module/root pairs are imported from Increment 04 without resource changes:
`nutanix-domain`, `nutanix-workload`, `nutanix-route`, `nsx-domain`,
`vsphere-workload`, `nsx-route`, `nsx-gateway-quarantine`, `openstack-domain`,
`openstack-workload`, `openstack-route`.

Child modules declare providers; roots configure them and the deliberately incomplete
remote backend. Operator examples are disabled. Quarantine/destruction guards remain.
No module claims complete firewall/ZIP, installer or live platform qualification.

Run `python tools/verify_terraform.py --mock-tests` from the repository root. The
verifier copies the source into a temporary directory, disables backend initialization,
validates real provider schemas and runs plan-only provider mocks when available.
Generated schema and lock outputs are under ignored `build/reports/`; review locks
before copying the appropriate actual `.terraform.lock.hcl` files into owned roots.
The copied pins are explicit versions, not a claim that they are the newest supported
combination for your environment.

**Current native engine status is BLOCKED**, not a Python-validation pass. The CI
job is authored to run the real gate after your local commit/push; it has not run on
GitHub as part of this ZIP creation. See [testing](../docs/TESTING.md).
