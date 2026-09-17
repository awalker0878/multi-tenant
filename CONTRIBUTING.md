# Contributing

Start from the architecture or engineering record that authorizes the change. Use
one owned resource scope per module or role. Do not use a Terraform provisioner to
hide an unsupported native operation. Do not let Ansible and Terraform manage the
same native object independently.

Run the gates in [TESTING.md](docs/TESTING.md), report blocked checks explicitly, and
keep actual native integration evidence separate from mocks and local fixtures.
New reference revisions get a new versioned artifact path and a catalogue update;
old approved files are not silently overwritten.

Run `python scripts/catalog_artifacts.py` after adding documentation, then
`python scripts/check_repository.py`. Never execute historical generators under
`reference/` merely to satisfy a current test. Those scripts belong to their recorded
release and may reference historical authoring paths.

Generated `.terraform.lock.hcl` files should be reviewed and committed after the
actual provider toolchain runs. Do not commit `.terraform/`, live variable/backend
files, binary plans or state. Current reports live in ignored `build/reports/`.
Only sanitize and deliberately copy a release summary into `evidence/`.
