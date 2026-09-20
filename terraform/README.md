# Terraform deployment scopes

| Path | Purpose |
| --- | --- |
| `modules/<component>` | Reusable provider-native resources; no backend or credentials |
| `stacks/components/<component>` | Individually owned execution roots with configured providers and an incomplete HTTP backend |
| `compositions/<platform>/<phase>` | Typed collections of native domain or workload modules for one tenant/WSD |
| `stacks/wsd/<platform>/<phase>` | Separate domain and workload execution roots; independently scoped state |
| `catalog.json` | Explicit module/root ownership and platform registry consumed by repository and engine checks |

Provider commissioning, security-edge controls and WSD allocation have distinct owners and state. A cluster is an eligible capacity pool, not a synonym for a tenant or WSD. Use the [cluster topology](../docs/engineering/cluster-topology-and-wsd-placement.md) to define actual placement and failure boundaries before applying a WSD scope.

## Existing state migration

The former `roots/<component>` directories moved to `stacks/components/<component>`. Component resources and `module.owned` addresses are unchanged. Preserve the **same backend and state key** when relocating an existing checkout; do not initialize a new empty state against existing resources. The directory move alone requires no resource-address migration. Stop if the plan proposes recreation. Separate review and native ownership verification are required before importing or changing ownership.

## Validation and execution

Run `python tools/verify_terraform.py --mock-tests` from the repository root with Terraform 1.13.5 available. The catalogue rejects omitted or duplicate configurations. The verifier copies every registered module and root into a temporary directory, initializes with backend disabled and reviewed dependency locks, validates real provider schemas, and runs plan-only provider mocks. Reports are written under ignored `build/reports/`. These checks do not establish native qualification.

Actual backend settings, credentials, inputs, plans, state and evidence stay in private operator storage outside Git. Provider pins describe the reviewed toolchain, not the installed platform's supported tuple. Build defaults remain disabled; production activation is not implemented by the restricted component modules. Follow the maintained [automation delivery program](../docs/implementation/automation/README.md) for acceptance and remaining integrations.

The [WSD deployment runbook](../docs/implementation/automation/wsd-deployment.md) explains composition boundaries, output handoffs and migration. Regenerate interfaces after a primitive change with `python scripts/build_wsd_compositions.py`; `--check` detects stale generated interfaces.
