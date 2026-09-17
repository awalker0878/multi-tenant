# Ansible: offline preparation and validation

New repository code, not an imported playbook from Increment 04. The baseline contained Terraform and Python, but no Ansible implementation.

Run `bash ansible/tests/validate.sh` using ansible-core 2.19.3. This checks syntax, exercises check mode, renders a repository-local preparation manifest, proves second-run idempotence, and rejects native-contact and cross-tenant fixtures.

No SSH, vendor API, installed service or infrastructure configuration is changed. Check mode executes the validation assertions but intentionally skips local rendering. Passing this harness does not validate a native switch, hypervisor, firewall, backup service or authorization. Production inventories and credentials do not belong in this repository.

Separate future native roles by the architecture's foundation, platform, edge, domain, workload and shared-service ownership boundaries. Do not use Ansible to create a second writer for a Terraform-owned resource.
