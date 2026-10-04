# Synthetic Kubernetes foundation

P01.02/P01.05 candidate renderer for the same seven applications, nginx public-root
proxies and PostgreSQL identities as the [local fixture](../local/README.md).
Rendering or passing the static boundary tests is **not** installation evidence.
No Kubernetes campaign has been measured by this change. This fixture does not
select an operated Kubernetes distribution, CNI, PKI, storage or secret provider.

`candidates.json` records primary-source candidates: kind **v0.33.0**, its published
Kubernetes **v1.36.4** node digest, Helm **v3.22.0** and Cilium **1.20.2**. The selected Kubernetes
minor is in Cilium's documented compatibility matrix. The newer kind default is
not implicitly adopted. Verify the kind and Helm downloads against the recorded
upstream SHA-256 values. Resolve the Cilium chart digest and every rendered Cilium
image before running the integration campaign.
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
