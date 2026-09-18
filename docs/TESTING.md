# Test strategy and actual evidence levels

The active reference describes the infrastructure; the tests evaluate specific code
and observations, not organizational authorization. [Terraform guidance](../terraform/README.md)
and [Ansible boundaries](../ansible/README.md) describe the two execution surfaces.

## Toolchain and commands

Use Python 3.13 for parity with the authoring environment. Install dependencies from
an approved source using `requirements-repository.txt` for local checks or
`requirements-dev.txt` for the Ansible engine. CI selects Terraform **1.13.5** and
Ansible Core **2.19.7** as explicit candidate bootstrap versions, not as a statement
that they are the newest releases or the approved production combination.

```sh
python -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements-dev.txt
python scripts/check_repository.py
python tools/check_local.py
python scripts/verify_ansible.py
python tools/verify_terraform.py --mock-tests
```

| Gate | What actually executes | What a pass does not establish |
|---|---|---|
| Repository | Source shapes, common-secret patterns, links, frozen bytes, mock-test guard, YAML structure | Engine parsing, exhaustive security review, native compatibility |
| Local regressions | Python functions and disposable loopback HTTPS/DNS/TLS fixtures; route-model cases | Native product behaviour, routed IPv6 or full ZIP qualification |
| Ansible engine | Actual syntax checks, local template/file tasks, second-run zero-change, check-mode non-mutation and negative fixtures | Remote host configuration, switch support, native contacts |
| Terraform engine | Backend-disabled init/validate, real plugin schemas and plan-only provider mocks on ten module/root pairs | Live provider API support, infrastructure conformance, safe production apply |
| Routed-family laboratory | Separate fixed IPv4 and IPv6 namespace packet/TLS campaigns, plus exact-source report completeness | Native IPv6, vendor HA, production DNS/PKI or authorization |
| Other manual labs | Additional fixed disposable protocol campaigns | Native product qualification or authorization |
| Native qualification | Separate approved target and engineering procedure | Not executed or automated by repository CI |

`make test` means the first two gates only. `make test-all` additionally requires both
engines and fails if either is unavailable. Missing tools never return a passing engine
result. YAML parsing and pure Jinja rendering must not be reported as Ansible syntax
or idempotence tests. Terraform test mocks still require real installed provider
schemas; Python source checks do not replace them. [R1; R2]

## Terraform trust and isolation

Initialization downloads and executes provider packages. Use trusted mirrors,
reviewed version pins and real generated checksums. The verifier removes ambient
platform credentials, copies the source to a temporary directory, disables backend
initialization and never invokes a native apply or a live plan. Module tests must
explicitly mock all required providers and use `command = plan`; real-provider blocks,
provider remapping and alternate module sources are refused by the guard.

The guard is lexical, not a full HCL parser or a sandbox for malicious source.
Review all resources, providers and tests before execution. Engine/schema diagnostics
are required before changing the candidate status. Generated locks and schema exports
are captured under `build/reports/`; locks must be reviewed and committed to their
corresponding module/root locations through a separate change. Do not invent them.

## Ansible ownership

No Ansible source existed in the imported increment. These new roles use only core
modules. The staging role writes two reference files in a caller-marked local directory;
it cannot create a native VM, route or firewall policy. The other role invokes only the
fixed native reader's input-validation mode, without contact flags. Defaults opt out.

The engine verifier executes first-run staging, repeat staging, check-mode drift
simulation, disabled and foreign-owner rejection and no-contact reader validation.
Check mode is a simulation; the verifier additionally compares staged bytes before and
afterwards. Unsupported/skipped actions are not real observations. [R2; R3]

## CI and cost/safety boundaries

The regular workflow has independent repository, Terraform and Ansible jobs, using
GitHub-hosted Ubuntu 24.04. The routed-family laboratory runs on pull requests, `main` pushes and manual dispatch.
Other retained laboratory workflows keep their separate manual-dispatch scope.
All actions are pinned to observed full commit IDs, repository permissions are read-only,
checkout credentials are not persisted and no native secrets or deploy job are used.
The original import did not execute the workflows. Subsequent runs and the current
change are tracked by their exact Git revision and Actions artifacts, not by treating
that historical delivery note as current status.
Jobs may consume your private repository's Actions allowance when pushed or dispatched.

Do not run unreviewed pull-request code on privileged self-hosted infrastructure.
No job is allowed to use `pull_request_target`, native credentials or an environment
with access to production systems. Package trust and dependency updates still require
review; direct version pins are not a complete transitive supply-chain lock. [R4]

## Reports and preservation

Current reruns write to ignored `build/reports/`. Imported `quality/` reports remain
historical, including their original failures and earlier test counts. The sanitized
repository-release snapshot is under [evidence/repository-import](../evidence/repository-import/README.md).
No current check relabels a frozen Word document or old report as newly approved.
Reference Word/Excel bytes are preserved, not edited, re-rendered or recalculated.

## Primary implementation references

- R1: [Terraform provider mocks](https://developer.hashicorp.com/terraform/language/tests/mocking).
- R2: [Ansible check and diff mode](https://docs.ansible.com/projects/ansible/latest/playbook_guide/playbooks_checkmode.html).
- R3: [Ansible template module](https://docs.ansible.com/projects/ansible/latest/collections/ansible/builtin/template_module.html).
- R4: [GitHub secure workflow guidance](https://docs.github.com/en/actions/reference/security/secure-use).

Reviewed for repository design; exact installed component qualification remains separate.


## Documentation migration gate

Run `python scripts/check_documentation.py` to verify full source conversion, table and field retention, diagram bytes, local Markdown anchors and source-backed ADRs. This does not rewrite documents, fetch sources, execute Terraform/Ansible, contact a target, or issue architecture acceptance. Reports are written only below `build/reports/`.


## Completion-corrective release verification

`python tools/check_release.py` checks a clean current Git checkout, not the historical file list. Exported releases require their explicit snapshot manifest. `python scripts/check_documentation.py` adds independently parsed code/tab/break fidelity, ordered table cells, exact ADR rendering/lifecycle, maintained design records and complete test/allocation indexes. `tools/verify_terraform.py --mock-tests` exports schemas from backend-free modules only, validates roots with `-backend=false`, and validates committed locks read-only. Passing that job does not contact native services. Ansible negative checks require genuine failed local assertions, not timeouts. Current CI source hashes and run identity are recorded in reports.

## Routed IPv6 local packet extension

[Run the fixed IPv6 campaign](implementation/routed-ipv6-lab.md) after the [engineering scope](engineering/routed-ipv6-qualification.md) is understood. `python lab/run_ipv6_lab.py --execute` requires nftables and authorized namespace/sysctl capabilities and produces a new private `build/reports/local_ipv6_packet_lab.json`. The hosted disposable lab job supplies explicit privilege; it does not disable host security settings. The ordinary unit suite covers its message/guard/source logic separately. A blocked runtime is nonzero, not a skipped pass, and native IPv6 remains unqualified.
