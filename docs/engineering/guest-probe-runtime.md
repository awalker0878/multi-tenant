# Package-owned fixed guest probe

Reviewed 3 October 2026. This B05 continuation follows the
[enterprise workload mobility execution plan](../product/enterprise-workload-mobility-execution-plan.md).
It moves the fixed read-only guest probe from `tools/guest_probe.py` to
`provisioner.execution.guest_probe`. The former path is deleted and retired; no
forwarding module or alternate probe is retained.

The probe's behavior is unchanged. It verifies the expected machine ID, binds the
explicit source address, attempts one bounded IPv4 connection, requires TLS 1.2+ and
the supplied CA/name for allowed cases, refuses redirects/error bodies as health,
checks a fixed response-body SHA-256, and returns only the existing bounded statuses.
The ten-second process alarm and three-second socket timeout remain unchanged. It does
not install software, change guest state, discover destinations or grant execution.

`tools/qualify_target.py` still owns campaign orchestration but now reads the fixed
probe source from the installed package path. Installed-distribution tests require the
new module in the wheel, absence of the old tools module and stale bytecode, and exact
resolution from an unrelated working directory. Target-campaign loopback TLS tests
continue to exercise machine binding, health and denial-control semantics.

This ownership move does not qualify a guest, network path or platform. The campaign
still requires separately authorized native observations, pinned SSH identity, owner
approval and current evidence. Other direct operator/native observer tools, execution
journals, installed service composition and retained-state conversion keep B05 open.
