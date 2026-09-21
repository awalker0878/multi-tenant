# Bootstrap a private GitLab state project

`tools/state_project.py` creates a dedicated private project in an existing
accepted GitLab namespace and publishes exact backend configurations for its
accepted state scopes. It implements the project bootstrap part of W03 using
the [selected GitLab state service](reference-realization.md#state-service-setup).
It performs one project-creation POST, records durable intent first, and recovers
an uncertain response through read-only native identity/settings observations.
It never writes a Terraform state file, edits an existing project, grants a role,
changes group membership, initializes a repository, retries creation or deletes
anything.

## State custody before creation

The independently recoverable GitLab service and private group already exist.
Select the exact installed GitLab version, group ID/path, namespace-owner user
ID and complete inherited membership. This REST v4 profile uses the package
visibility controls available from GitLab 18.5, accepts the 18/19 major families,
and checks the exact installed version on every observation. This interface
range is not installed-version qualification; accept and exercise the actual
service tuple first.

Use a bounded bootstrap access token for the accepted namespace owner, separate
from Terraform's state token. The tool verifies the authenticated user, rejects
an explicitly reported instance administrator, and requires the accepted owner
role in the namespace member list. GitLab's ordinary current-user response can
omit the administrator field; independent service acceptance establishes the
credential's actual privilege. The API supports [Bearer access-token headers](https://docs.gitlab.com/api/rest/authentication/).
Do not put tokens in URLs, source files or public CI.

A project is one accepted credential boundary. All requested state scopes must
share environment, site, platform and tenant. Use separate private namespaces
where different tenant custodians must not inherit each other's state access.
The accepted member list includes every inherited user, including the bootstrap
owner and existing runner identities. Standard roles only are supported; custom
roles, inactive users, expiring memberships, group sharing or unexpected members
hold this bootstrap. Membership changes and token enrollment have a separate
identity owner; this tool cannot grant them implicitly.

GitLab documents that Developer-or-higher members can read state, while locking
and state removal require Maintainer-or-higher roles. Treat state as sensitive:
a runner with sufficient lock permission also has powerful state permissions.
Independent backup/delete protection remains necessary. See
[GitLab-managed state permissions](https://docs.gitlab.com/user/infrastructure/iac/terraform_state/).

## Private input contract

A `hosting-state-project/1` request has exactly:

| Field | Required value |
| --- | --- |
| `format`, `enabled` | `hosting-state-project/1`; boolean enabled only for an accepted operation |
| `source_commit`, `operation_id` | Exact clean source SHA and stable operation identifier |
| `origin`, `gitlab_version` | Canonical HTTPS service origin without trailing slash and exact installed version |
| `namespace_id`, `namespace_path`, `path` | Existing private group ID/path and new project path; lowercase alphanumeric/hyphen segments |
| `actor_id` | Accepted namespace owner's native user ID |
| `members` | Sorted unique `{ "id": integer, "access_level": integer }` list; standard roles 10/20/30/40/50, including the actor at 50 |
| `scopes` | Sorted unique complete backend scopes: `environment_key`, `site_key`, `platform`, `tenant_key`, `wsd_key`, `phase`; phase is `domains` or `workloads` |
| `service_acceptance_ref`, `recovery_ref` | Accepted installed service and independent recovery records |

Sort scopes by their compiled `state_key`. Stage the request, token, authority,
optional CA bundle and shared ledger in owner-only storage outside the checkout.

A separate `hosting-state-project-authority/1` object has exactly `format`,
`request_sha256`, `action`, `valid_from`, `valid_until`, `change_ref`,
`token_sha256` and `ca_sha256`. The request digest is
`tools.readback_core.digest(request)`. Credential/CA digests bind their complete
file bytes; absent CA uses null and the system trust roots. Authority lasts at
most one hour, is checked before each request, and selects either `create` or
`observe`. Observation never authorizes another POST.

```sh
python tools/state_project.py --request /private/state/project.json
python tools/state_project.py --request /private/state/project.json \
  --action create --authority /private/state/create-authority.json \
  --token-file /private/state/bootstrap-token --ca-file /private/state/ca.pem \
  --ledger /private/state/owner-ledger --execute
```

The default command validates without contact. Explicit creation checks the
exact source and service, authenticated actor, private unshared namespace and
complete paginated membership before checking that the exact project path is
absent. It then journals intent and submits the fixed private project profile.
The profile disables pipelines, instance/group runners, Auto DevOps, access
requests, public jobs and unrelated project features; infrastructure visibility
is member-only. It supplies no import URL, template or repository content.
The [GitLab Projects API](https://docs.gitlab.com/api/projects/) documents the
creation fields and the paired package-disable settings.

The returned native project ID is retained even if later readback fails. The
tool verifies project identity, namespace, creator, ownership marker, all owned
settings and the complete inherited member list, then repeats project and
namespace observations. It never accepts omitted required settings as defaults.
Responses containing private fields unrelated to the accepted handoff are not
copied into receipts.

## Recovery and backend handoff

After any creation attempt, repeat only with `--action observe` and new exact
observation authority. The shared ledger is scoped to origin and canonical
project path; a renamed operation cannot evade an earlier intent. If the POST
response was lost, recovery looks up that path and requires the exact request
marker, creator, namespace and configuration before retaining the observed ID.
If an ID was previously recorded, a replacement object cannot be substituted.
A still-absent, foreign or partially configured project remains held. Even a
matching pre-existing project without this journal requires separately accepted
adoption; the tool does not infer custody from a name.

The receipt status is `PRIVATE_STATE_PROJECT_OBSERVED_REQUIRES_COMMISSIONING`.
It contains the narrow current project/group observations and a `backends` map
from exact `state_key` to the real `tools/state_backend.py` output. Persist the
selected map entry as the executor's private `backend.json`, retaining the
receipt digest and exact scope. No operator has to guess or manually edit the
native project ID between creation and backend preparation.

Every observation rechecks live settings and membership; an old successful
receipt cannot hide drift. Concurrent filesystem writers serialize, but this
local journal does not fence GitLab administrators or detect coordinated deletion
of its complete history. Retain independent custody. Administrative correction
of a held project's settings requires its own accepted operation; observation
can then verify the same retained project without another creation.

Before state use, commission actual runner access, cross-project denial,
concurrent Terraform locks, encryption, version retention and independently
recoverable GitLab database/object-store/encryption secrets. These are separate
facts: project creation does not prove them. This tool neither overwrites state
for a test nor restores an old state as an infrastructure rollback.

## Test evidence

`tests/test_state_project.py` exercises actual HTTPS requests and JSON bodies
against disposable GitLab-shaped responses. It covers exact creation/handoffs,
lost replies, unknown absence, existing projects, wrong identities/versions,
unexpected inherited access, pagination faults, configuration drift, expired or
changed credentials, journal failure, competing writers, redirects and untrusted
TLS. The fixture establishes transport and recovery behavior; an installed
GitLab service has not been commissioned by these tests.
