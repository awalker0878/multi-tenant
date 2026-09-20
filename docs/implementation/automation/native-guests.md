# Native guest configuration

The candidate Linux profile is `ansible/playbooks/native/configure_linux.yml`. Its current target is an Ubuntu 24.04 systemd guest image with Python 3 and chrony already installed. This is a concrete configuration implementation, not a qualified image offer. Windows, other Linux images, package/patch/reboot workflows and product-specific service enrollment remain open work.

Terraform owns the VM, network, storage and lifecycle resources. Ansible owns only the guest hostname, `/etc/chrony/chrony.conf`, `/etc/sysctl.d/60-hosting-guest.conf`, the corresponding live forwarding/redirect controls and chrony service state. This role is for ordinary workload guests; never select it for routers, appliances, nested platforms or container hosts that require forwarding. Review existing ownership before adopting these files.

## Required handoff

First complete independent image/provenance and native VM/placement verification, the accepted restricted-bootstrap transition, entitled time-service paths and scoped SSH/sudo access. Restricted Terraform defaults do not start and expose all guests. This playbook cannot establish reachability by weakening platform quarantine.

Capture the workload root's `terraform output -json` privately. Create one `hosting-guest-access/1` JSON document with these fields:

| Field | Required value |
| --- | --- |
| `format` | `hosting-guest-access/1` |
| `scope` | Exact workload output scope: environment, site, platform, tenant, WSD and `phase: workloads` |
| `valid_until` | Timezone-qualified future timestamp, at most 24 hours away |
| `change_ref` | Separately issued change reference; a string is not signature/approval verification |
| `targets` | Map with exactly the workload output member names |

Each target contains `native_id` matching the VM/server output; observed SSH `address`, `port`, non-root `user`, exact `host_key` (`ssh-ed25519` plus its base64 public key); independently observed 32-character lowercase `machine_id`; approved short `hostname`; `profile: ubuntu-24.04-chrony`; and one to four entitled `time_servers` as IP addresses. Machine IDs must be unique per guest. Obtain keys, address bindings and machine IDs through trusted image/native provisioning observation; a scan of an unauthenticated endpoint does not establish that binding. Do not store private keys or passwords in this file.

```sh
python tools/guest_inventory.py /private/operator/workload-outputs.json \
  /private/operator/guest-access.json --output /private/operator/new-guest-run
cd ansible
ansible-playbook -i /private/operator/new-guest-run/inventory.json \
  playbooks/native/configure_linux.yml \
  -e '{"hosting_native_enabled": true}' --check
```

Run the same approved command without `--check` to configure the accepted target. The parent output directory must exist; the builder creates a new 0700 directory and 0600 inventory/known-hosts files and refuses overwrite. Use the pinned `requirements-dev.txt` toolchain and scoped SSH-agent credentials. Ansible's [SSH connection](https://docs.ansible.com/ansible/latest/collections/ansible/builtin/ssh_connection.html) uses explicit host-key checking, batch mode and the generated key file. Do not override connection parameters, skip guard tasks, or treat this playbook as a sandbox for untrusted operators.

## Execution and recovery behavior

The first play validates the entire inventory locally before SSH, including output identity, target set, expiry, host keys and disallowed connection overrides. The native play requires that gate even if `--limit` skipped localhost. It checks expiry again per host, reads `/etc/machine-id` without escalation, then checks the OS. Guests run serially; any failed check stops the invocation. Privilege escalation is scoped to owned configuration and time verification.

The role validates the chrony template with the installed daemon before replacement, restarts chrony on change, reconciles only its eight live sysctl keys and waits for time synchronization. Persistent file and live sysctl checks both run, so a repeated run can repair live drift even when the file is unchanged. Check mode reads identity/facts/kernel controls and predicts changes without applying or waiting for synchronization. A failed synchronization check leaves the guest restricted; it does not activate service or roll back other owners' controls.

Store controller logs and observed results privately with the exact source/input hashes. If interrupted, reconcile the actual guest, its platform task and the still-current handoff before rerunning. This serial playbook does not fence another controller, authorize automatic rollback or prove useful-data recovery.

## Evidence boundaries

CI performs real Ansible syntax checking and proves disabled or malformed native invocations fail before contact. Python tests cover changed scope/resource IDs, expired handoffs, unsupported profiles, unsafe addresses, replaced key files and changed connection settings. Local staging idempotence/check-mode tests remain separate. Native guest convergence, time behavior, interruption/reboot recovery and actual least-privilege credentials still require a selected target. The profile does not configure identity/PKI/KMS, resolver, backup, telemetry, package services, SSH hardening or production connectivity; these require their selected interfaces and accepted service handoffs.
