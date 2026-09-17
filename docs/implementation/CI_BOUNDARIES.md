# Validation boundaries and actual observations

CI tests configuration, not production readiness. It uses GitHub-hosted disposable runners, pinned action revisions, read-only repository permission, no retained checkout credential and no native inventory or secrets.

Terraform 1.13.5 initializes ten modules and roots with `-backend=false`, validates them against installed provider schemas, exports schemas from modules, and runs only explicitly mocked plan tests. Root HTTP backends remain uninitialized: `providers schema` on those roots asks to initialize the backend even after successful validate. The initial run exposed this test-harness error; the corrected workflow exports module schemas rather than contacting state storage. No apply or destroy is part of CI.

Ansible-core 2.19.3 exercises a newly written localhost-only manifest role. It checks syntax, runs assertions in check mode, renders a private local JSON file, confirms the second run is unchanged, and rejects attempted native-contact and foreign-tenant fixtures. It does not provision a switch or hypervisor. Initial Actions run 35258773557 passed this Ansible job.

Provider lockfiles and schema/plan-test reports are retained in private short-lived run artifacts. Native service credentials, states, actual-input inventories and production evidence are excluded. Historical authoring reports are not current validation evidence. Failure remains visible; no continue-on-error or fabricated pass is used.

Primary method references: HashiCorp Terraform provider-mocking documentation; Ansible check-mode documentation; GitHub Actions secure-use reference. These methods do not replace installed-platform qualification, packet-path observations, recovery acceptance or authorization.
