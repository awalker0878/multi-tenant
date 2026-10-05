# Synthetic Kubernetes foundation

P01.02/P01.05 candidate renderer for the same seven applications, nginx public-root
proxies and PostgreSQL identities as the [local fixture](../local/README.md).
Rendering or passing the static boundary tests is **not** installation evidence.
The first campaign installed Cilium and the application foundations, then failed
an application health-contract assertion; a passing campaign remains pending.
This fixture does not select an operated Kubernetes distribution, CNI, PKI, storage
or secret provider.

`candidates.json` records primary-source candidates: kind **v0.33.0**, its published
Kubernetes **v1.36.4** node digest, Helm **v3.22.0** and Cilium **1.20.2**. The selected Kubernetes
minor is in Cilium's documented compatibility matrix. The newer kind default is
not implicitly adopted. Verify the kind and Helm downloads against the recorded
upstream SHA-256 values. Verify the Cilium chart against the recorded observed
archive and OCI digests, and require immutable rendered Cilium images.
`cilium-values.json` selects Kubernetes IPAM, retains kube-proxy and reduces the
synthetic operator to one replica. Cilium's node-level privileges are a separate
cluster prerequisite; product application pods receive none of them.

Primary references, checked 2026-10-04:

- [kind release and published node identities](https://github.com/kubernetes-sigs/kind/releases/tag/v0.33.0)
- [kind image import and pull policy](https://kind.sigs.k8s.io/docs/user/quick-start/)
- [kind Linux binary metadata and digest](https://api.github.com/repos/kubernetes-sigs/kind/releases/assets/531396433)
- [Helm release and published archive checksum](https://github.com/helm/helm/releases/tag/v3.22.0)
- [Cilium installation on kind](https://docs.cilium.io/en/stable/installation/kind/)
- [Cilium Kubernetes compatibility](https://docs.cilium.io/en/stable/network/kubernetes/compatibility/)

## Generate without installing

Supply the same seven immutable local Docker image configuration IDs consumed by
the local installer. Create a private directory outside the checkout, owned by the
current user with mode `0700`, and choose an absent child for `--runtime`:

```sh
python scripts/p01/kubernetes_runtime.py \
  --workspace "$PWD" --runtime "$PRIVATE_PARENT/runtime" \
  --images /absolute/path/to/application-images.json \
  --source-revision "$SOURCE_REVISION" --namespace p01-integration
python -m unittest discover -s scripts/p01 -p test_kubernetes_runtime.py -v
```

The renderer reuses local fixture generation for unique disposable secrets and
seven-day TLS certificates, including each proxy's Kubernetes Service names in its
leaf certificate SANs and exact nginx Host allowlist. Other services, namespaces
and arbitrary domain suffixes remain rejected. It creates these additional files:

| File | Use |
| --- | --- |
| `kind.json` | Two-node isolated cluster, API bound to loopback, default CNI disabled, published node digest |
| `namespace.json` | Dedicated `p01-` namespace |
| `resources.json` | Accounts, ConfigMaps, private Services, fifteen Deployments, PostgreSQL PVC and network policies; secret references only |
| `migrations.json` | Seven controlled migrator Jobs, separate from runtime deployment |
| `secrets.json` | **Private secret payloads. Never retain or publish this file.** |
| `image-imports.json` | Application config-ID and dependency manifest-reference mappings to derived kind-local tags |
| `fixture.json` | Source revision and explicit rendered-only scope |

Never commit, upload, print or retain the complete runtime directory as evidence.
It also contains the generated CA private key, mounted secret files and Compose
inputs. Only explicitly reviewed non-secret manifests and observations can become
evidence. Kubernetes Secrets are ordinary synthetic in-cluster objects, not proof
of external secret custody or encryption at rest.

## Run the installation campaign

The executable campaign is [`run_kubernetes.py`](../../scripts/p01/run_kubernetes.py).
It requires a clean checkout at the supplied full Git revision, a Linux/amd64
Docker host and connected access to the declared source/package/image registries.
Choose an absent evidence directory outside the checkout:

```sh
python scripts/p01/run_kubernetes.py \
  --workspace "$PWD" --output "$EVIDENCE_OUTPUT" \
  --source-revision "$SOURCE_REVISION"
```

Without `--images`, the campaign builds and verifies all seven application images
with the existing image runner, up to three builds concurrently. To reuse already
built local images, add `--images /absolute/path/to/application-images.json`.
That file must map exactly the seven service names to immutable Docker
configuration IDs. The campaign verifies each image's source-revision label,
owning-component label, OS and architecture; matching names alone are insufficient.
`--workspace` otherwise defaults to this repository root. The campaign creates its
own unique cluster/namespace, private runtime directory and dedicated kubeconfig;
the operator's current Kubernetes context is not used.

The [Kubernetes integration workflow](../../.github/workflows/p01-kubernetes-integration.yml)
runs installer tests before the campaign, has a 55-minute job limit and uploads
the separate evidence directory even after failure. Its current artifact retention
is 14 days. A failed or incomplete campaign remains a failure; the renderer's
`fixture.json` continues to identify rendering scope independently of the measured
campaign result.

### Artifact checks and Cilium's first observation

The runner checks kind and Helm bytes against committed SHA-256 values and checks
their reported versions. It downloads the kubectl version matching the selected
node, verifies its freshly retrieved upstream checksum and records both values;
that kubectl checksum is an observed input, not a previously committed byte pin.
The kind node's observed registry digest must match the recorded node reference.

The [first campaign](https://github.com/awalker0878/multi-tenant/actions/runs/37245679773)
pulled Cilium 1.20.2 with `mode: first_observed_candidate`, required exactly one OCI
digest in Helm's output, hashed the downloaded archive, rejected rendered images
without immutable `@sha256` references and installed that same archive. Cilium
installation completed before a later application health-contract assertion
failed. Its [observed chart identities](../../verification/p01/kubernetes/run-37245679773/cilium-observed-lock.json)
are now recorded as `chart_sha256` and `chart_oci_digest` in `candidates.json`, with
the source revision, workflow and retained artifact provenance. Subsequent
campaigns must verify both and report `locked_replay`. The first observation was
not a pre-existing chart lock; neither it nor replay provides signature verification
or trusted promotion evidence.

### Retained evidence and cleanup

| Evidence | Recorded scope |
| --- | --- |
| `report.json` | Source revision/hashes, command results, individual checks, tool and image identities, Cilium chart mode, fixture hashes and cleanup result |
| Numbered stdout/stderr logs | Command arguments, exit codes, elapsed time, timeout observations and output byte hashes; stdin is not copied into these logs |
| `images/<service>/` and build-runner logs | Per-image build/verification evidence when the campaign performs the builds |
| Six non-secret generated JSON manifests | Namespace, resources, migrations, kind configuration, image-import map and rendered fixture scope |
| `cilium-observed-lock.json` and chart-render logs | Actual archive/OCI identity and rendered image references |
| Pod/policy inventories and bounded container logs | Installed resource/image observations and up to 200 lines per captured application, proxy and PostgreSQL deployment |

The runner does not copy `secrets.json`, mounted secrets, CA private key or its
kubeconfig to the evidence directory. Diagnostic Pods mount only their owning
health token and CA, without database credentials. Password/token values are read
inside containers instead of being passed in recorded command arguments. The
collector retains raw command output, so these exclusions are not a general-purpose
log redactor; retained outputs still require review before publication.

Normal completion and handled failures enter cleanup. Failure to collect a
deployment's logs is recorded and does not prevent attempting deletion of the
uniquely named owned kind cluster. Successful deletion records `cleanup_complete`
and removes the private parent directory, including credentials and kubeconfig.
If cluster deletion fails, the campaign changes the result to `FAIL`, records
`cleanup_complete: false` and preserves the private directory for recovery.
An explicit `--keep` skips cluster/private-directory deletion for diagnosis; it
must not be described as completed cleanup. Forced process termination can prevent
Python's cleanup block from running and requires checking the owned cluster name.

## Required measured installation order

1. Verify the tool, node, chart and image identities against their recorded pins.
   Import built application images into kind using `image-imports.json`: create each
   derived local tag from its recorded immutable configuration ID, verify the tag
   still resolves to that ID, then load it. A Docker configuration ID is not an OCI
   registry-manifest digest. Pull each dependency by its canonical pinned manifest
   reference, record the observed configuration ID and create its separately named
   manifest-derived local tag. Verify configuration IDs before and after import.
   The derived tags avoid losing canonical digest aliases during Docker archive
   import; they do not replace the recorded immutable source identities. All
   product containers use `imagePullPolicy: Never`.
2. Create a uniquely named disposable kind cluster with `kind.json` and a dedicated
   kubeconfig inside the private directory. Do not use the operator's default
   kubeconfig. Install the resolved Cilium chart with the provided values and
   inspect the actual agent/operator images and policy enforcement health.
3. Apply `namespace.json`, privately apply `secrets.json`, then apply
   `resources.json`. PostgreSQL uses a one-replica Recreate Deployment and a PVC
   from kind's default development storage provisioner; this is not HA storage.
4. Wait for PostgreSQL's startup/readiness checks, then apply `migrations.json`.
   Every Job authenticates over verified TLS using only its own migrator secret.
   Require all seven Jobs to complete successfully. Capture their non-secret
   migration identity/version output. Failed Jobs are not silently retried.
5. Wait for application foundation dependency readiness. PHP executes its existing
   authenticated dependency Action through the bootstrapped application; Python
   probes its authenticated HTTP dependency endpoint. Application liveness only
   checks the process port. Product `/health/ready` still returns 503 because the
   product services remain foundations. Proxy readiness measures its listener only.
6. Run real permitted and denied pod-to-pod checks, wrong-identity/schema-version
   tests and a PostgreSQL outage/restart observation. Check observed pod image
   identities against imported artifacts. Retain source, cluster/tool versions,
   commands, results and reviewed non-secret resource inventory. Do not infer a
   successful installation from admitted manifests or Pod phase alone.
7. Delete only the uniquely named disposable cluster and private fixture created by
   that campaign. Remove synthetic secrets and its dedicated kubeconfig.

The PostgreSQL wrapper starts as UID 0 only to set data/socket/TLS ownership, with
read-only root, no privilege escalation and exactly `CHOWN`, `DAC_OVERRIDE`,
`FOWNER`, `SETGID`, `SETUID`; the official entrypoint drops to PostgreSQL's user.
Application, migration and proxy containers run as UID/GID 10001 with all
capabilities dropped, read-only roots and private writable volumes. Their service
accounts have no RBAC grants and automatic token mounting is disabled. PHP proxy
init containers use the same application image to copy only its `public/` tree.

## Network verification contract

Default ingress and egress are denied throughout the fixture namespace. Explicit
policies permit own proxy to app, each app/migrator to PostgreSQL, and DNS only to
the `kube-system` pods labelled `k8s-app=kube-dns`, TCP/UDP 53. PostgreSQL HBA and role
permissions separately restrict each identity to its owning database.

A campaign diagnostic pod may use labels `app.kubernetes.io/part-of=p01-foundation`,
`p01.role=probe`, `p01.service=<owning-service>` to access only that service's proxy
on 8443. Mount only its owning health credential and CA for authenticated checks.
These are synthetic workload selectors, not authentication of a human/operator.
Denied checks must include probe-to-database/direct-app, proxy-to-database,
cross-service proxy/app traffic and undesignated pod-to-proxy traffic. Observe actual
timeouts/denials with a positive control, rather than interpreting an unrelated
server failure as network enforcement. Node-originated traffic and API-server port
forwarding are not evidence that these pod-network policies work.

No broker, Temporal, evidence-store, native-platform access, workload execution,
operated identity custody, promotion admission or G01 pass is established here.

## Current campaign coverage and remaining integration work

The implemented campaign attempts authenticated dependency health, anonymous and
invalid-token denial, process liveness, unavailable product readiness, wrong CA,
foreign Host and protected-source-path checks for all seven applications. It
attempts runtime DML rollback plus DDL, migration-metadata-write, owner-role,
foreign-database, plaintext and bad-password denials. These SQL checks deliberately
run over PostgreSQL's loopback interface to isolate authentication/authorization
from the separate Cilium tests.

Its current network measurements are each diagnostic Pod reaching its own proxy,
timing out against a foreign proxy and PostgreSQL, plus the Planning application's
allowed PostgreSQL connection and denied Governance application connection.
Connection refusal or DNS failure does not count as a policy denial. Revoking the
Governance runtime login must fail its direct dependency probe; restoring login
must recover it. Scaling PostgreSQL down must fail every direct dependency probe
while application processes remain live; restarting it must recover health and
preserve the ordered fixture-data hashes on its existing PVC. Kubernetes removes
unready application endpoints, so a proxy error during this outage is distinct
from a directly observed application dependency response.

A passing campaign result is pending after the first failed attempt. Even a
passing result for this implemented scope leaves the following work separate:

- Retain migrator Job output showing the authenticated session identity and applied
  version. The current runner waits for Job completion but does not capture those
  Job logs as its deployment-log cleanup step.
- Measure schema-version mismatch and missing secret/key behavior in Kubernetes,
  migration replay/backfill behavior and the additional network paths specified
  above: proxy-to-database, probe-to-direct-app and undesignated Pod-to-proxy.
- Measure replay of the now-locked Cilium chart and complete the operated trust, DNS/PKI,
  storage, secret-custody and registry/provider inputs when that environment is
  selected. The fixture's Kubernetes ServiceAccount names are not product identity.
- Complete broker/outbox/inbox semantics, Temporal and worker integration, protected
  evidence storage, and the carried Permit Desk application/configuration fixture.
  Existing `foundation_records` are synthetic dependency records, not a complete
  representative application restore.
- Demonstrate independent service deployment, failed deployment recovery, restore
  from backup into an empty environment, alert delivery and the remaining G01
  review evidence. Restarting one PostgreSQL Deployment on the same PVC is a
  persistence/restart observation, not backup restore or the full recovery objective.
