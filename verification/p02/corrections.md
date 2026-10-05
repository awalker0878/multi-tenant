# P02 qualification corrections

The original observations remain unchanged. These are development results, not
receiving gate decisions.

| Source/run | Observation | Correction |
| --- | --- | --- |
| `d45d0aa83582c5376335c10d033b60d7e549d979`, [contract run 37353917453](https://github.com/awalker0878/multi-tenant/actions/runs/37353917453) | Existing local-identity schema bytes changed; the exact-version freeze rejected them. | `6fd44860f61d66bf858c92b8099f29a97479758b` restores the original published schema and its controller projection. The new federation API remains the source for current configuration state. No freeze rule or exclusion changed. |
| Same source, [P02 run 37353917458](https://github.com/awalker0878/multi-tenant/actions/runs/37353917458) | 55 PostgreSQL feature cases pass (952 assertions). Browser bootstrap, HTTPS provider configuration/handover and tenant creation work, but the reader test uses the preceding account URL because it samples before Inertia navigation finishes. The campaign is FAIL. | The test waits for the selected tenant heading before capturing its URL; authority assertions remain intact. |

The [failed P02 report](identity/run-37353917458/report.json),
[failed contract report](contracts/run-37353917453/report.json) and
[corrected original-baseline compatibility comparison](contracts/restored-compatibility.json)
are retained. The corrected comparison freezes the original accepted artifact
bytes at `f3612f6d5669ec47f13020a7f1f1f1d64e333e5d` and accepts only the three new
contract files. Its result does not relabel either failure. The [next contract run 37354292360](contracts/run-37354292360/report.json)
conservatively compares with the previous push and also sees the restoration as a byte change
relative to the rejected edit. The [unchanged-artifact regression at b1064b7](contracts/run-37354711828/report.json) passes the original unmodified check, along with generated-client and HTTP conformance replay. No failed run is treated as a passing gate.


## Governance delivery qualification

The initial `ab8570145870ed6d2c9d5c0a65a471f90e3315ab` runs are retained:
[identity/relay run 37358072207](identity/run-37358072207/report.json) and
[broker startup run 37358072439](events/run-37358072439/report.json).
The first exposed a timestamp precision mismatch: PostgreSQL's fractional
`available_at` default was compared with a Laravel seconds-only binding, making
new events appear temporarily unavailable. The second called the broker CLI
before its Erlang node finished starting. Neither is a passing campaign.

`4afcee1d504b8dfb0725d3306f8c2c55eb1f6dce` retains microsecond precision in the
relay eligibility comparison and waits for actual broker health/port readiness.
No authorization rule, time limit or assertion was relaxed. Corrected campaigns
37358891052 (identity/browser) and 37358890871 (PostgreSQL/TLS broker) pass;
their measured source remains distinct from subsequent delegation work.
