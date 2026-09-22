# Portable WSD request contract

One request document describes one **workload security domain**. It carries
consumer intent only: no provider-native identifiers, no Terraform state keys, no
VLAN/VNI values, no credentials and no approvals.

Schema: `provisioner/schemas/v1/workload-security-domain.schema.json`
(`$id: hosting.platform/v1/workload-security-domain`).

Reviewed examples: [`examples/requests/`](../../examples/requests).

## Top level

```yaml
apiVersion: hosting.platform/v1
kind: WorkloadSecurityDomain
metadata: {...}
spec: {...}
```

`apiVersion` and `kind` are constants. Both are checked before the schema so an
unknown version is reported as `UNSUPPORTED_API_VERSION`, not as a schema
violation. Unknown top-level keys are refused (`additionalProperties: false`).

## `metadata`

| Field | Required | Rule |
| --- | --- | --- |
| `tenant` | yes | `^[a-z][a-z0-9-]{1,23}$` — bounded by the native module limit |
| `name` | yes | `^[a-z][a-z0-9-]{1,40}$` — the WSD identity inside the tenant |
| `owner` | yes | `^[a-z0-9][a-z0-9-]{1,40}$` — the accountable owner |
| `description` | no | free text, at most 240 characters |

## `spec`

Required: `environment`, `security`, `platform`, `placement`, `availability`.

| Field | Form | Notes |
| --- | --- | --- |
| `environment` | string | resolved by the environment catalog; the lifecycle name |
| `security` | `{profile}` | required; selects the service class |
| `assurance` | `{profile}` | optional; defaults from the environment minimum |
| `platform.preference` | `auto \| nutanix \| vmware \| openstack` | `auto` evaluates every eligible candidate |
| `placement.region` | string | required |
| `placement.site` / `placement.cell` | string or `null` | a pin, not a bypass: a pinned value still has to be eligible |
| `availability` | `{profile}` | required |
| `network` | `{profile}` | optional |
| `recovery` | `{enabled, profile}` | `enabled: false` removes the recovery profile |
| `capacity` | `{computeProfile, storageProfile}` | optional; defaults come from the environment |
| `zones.operations` / `zones.restricted` | `{enabled}` | toggles; consistency with `availability` is enforced semantically |
| `services` | `{dns, ntp, identity, logging, backup}` | profile names inside the service family |
| `exposure` | `{publicIngress, internetEgress}` | both must be `false` in this repository |

### Rules that are enforced beyond the schema

* `internetEgress: true` is refused by standards rule `POL-EXPOSURE-002` — internet
  egress is not an implemented exposure path here.
* `environment: production` requires `availability` at rank `high` or above.
* `environment: recovery` requires `assurance` at rank `elevated` or above.
* Any `availability` above `single-zone` requires `zones.restricted.enabled: true`.
* A service profile whose declared `binding_class` does not match the reviewed
  endpoint at the selected site is refused with `SERVICE_UNAVAILABLE`.

## Parsing guarantees

`provisioner/domain/request.py` refuses duplicate mapping keys in both YAML and
JSON, refuses an empty or non-mapping document, and computes a canonical SHA-256
digest over the normalized document. That digest is the request identity used by
every later artifact, so two byte-different but semantically equal requests share
a digest while two different requests never collide.