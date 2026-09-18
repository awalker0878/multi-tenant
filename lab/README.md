# Disposable protocol and infrastructure fixtures

The namespace runner keeps the fixed two-tenant worked topology and original
33 routing/containment/recovery observations. It adds 14 mTLS/resource-identity
observations on the already permitted processor-01 to data-01 TCP443 path.
No new production protocol allowance or native policy is inferred.

```sh
python lab/run_namespace_lab.py --execute
python lab/run_dns_lab.py --execute
```

The first needs Linux user/network namespaces, iproute2, GCC and kernel netfilter.
It verifies the original namespace configuration, uses virtual links only and reaps
workers. TLS fixtures additionally use the pinned cryptography library for ephemeral
credentials. The second binds random loopback TCP ports, parses authenticated DNS
messages, and mutates only in-memory test records. Both require explicit --execute;
neither contacts customer infrastructure. Local unit tests also open bounded loopback
listeners and include actual IPv6 ::1 TLS endpoints.

The test DNS authority implements only the prereq/query/update subset needed by these
assertions, with fault injection and explicit name grants. It is **not** a server for
production or a certification harness for all of RFC 2136. Its code is intentionally
separate from the production-facing candidate client. No DNS data, TLS keys or test
listeners persist after the runs.

The v6 route/edge extension is not implemented by this fixture. Required IPv6 router
forwarding could not be commissioned in this runtime's read-only sysctl/mount scope;
no user-space forwarding proxy is presented as kernel/native IPv6 proof.

[DNS semantics and limits](../docs/DNS_LIFECYCLE.md) ·
[Identity semantics and limits](../docs/SERVICE_IDENTITY.md)
