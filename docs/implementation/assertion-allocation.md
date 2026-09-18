# Assertion-level implementation and enforcement allocation

**State: proposed engineering allocation; native verification and owner adoption are not claimed.** Each row retains its exact source requirement and identifies a narrower checkable facet, enforcement owner/location, related candidate artifact or external operating record, verification method and remaining dependency. A module link does not satisfy a requirement by itself.

All 194 requirements are represented. Compound requirements have explicit facets as well as an umbrella obligation that preserves anything not covered by a facet. The umbrella is not marked passed; the owner must finish scope analysis for each actual offered service. Not applicable requires an explicit rationale and authority, not a convenience flag.

| Family | Allocation rows | Read |
|---|---:|---|
| ACPT | 1 | [ACPT allocation](allocation/acpt.md) |
| API | 5 | [API allocation](allocation/api.md) |
| ARCH | 12 | [ARCH allocation](allocation/arch.md) |
| ASSUR | 13 | [ASSUR allocation](allocation/assur.md) |
| AUTH | 3 | [AUTH allocation](allocation/auth.md) |
| AUTO | 5 | [AUTO allocation](allocation/auto.md) |
| BKP | 8 | [BKP allocation](allocation/bkp.md) |
| CAP | 16 | [CAP allocation](allocation/cap.md) |
| CAT | 12 | [CAT allocation](allocation/cat.md) |
| CICD | 7 | [CICD allocation](allocation/cicd.md) |
| CMP | 5 | [CMP allocation](allocation/cmp.md) |
| CRY | 9 | [CRY allocation](allocation/cry.md) |
| DEL | 2 | [DEL allocation](allocation/del.md) |
| DOC | 8 | [DOC allocation](allocation/doc.md) |
| DRIFT | 7 | [DRIFT allocation](allocation/drift.md) |
| EDGE | 4 | [EDGE allocation](allocation/edge.md) |
| EGR | 2 | [EGR allocation](allocation/egr.md) |
| EVID | 16 | [EVID allocation](allocation/evid.md) |
| EVPN | 6 | [EVPN allocation](allocation/evpn.md) |
| EXC | 10 | [EXC allocation](allocation/exc.md) |
| EXP | 3 | [EXP allocation](allocation/exp.md) |
| FAB | 6 | [FAB allocation](allocation/fab.md) |
| FAIL | 9 | [FAIL allocation](allocation/fail.md) |
| FLOW | 3 | [FLOW allocation](allocation/flow.md) |
| FUT | 7 | [FUT allocation](allocation/fut.md) |
| IAM | 7 | [IAM allocation](allocation/iam.md) |
| IMG | 6 | [IMG allocation](allocation/img.md) |
| ING | 2 | [ING allocation](allocation/ing.md) |
| INV | 20 | [INV allocation](allocation/inv.md) |
| IPAM | 8 | [IPAM allocation](allocation/ipam.md) |
| IPV6 | 5 | [IPV6 allocation](allocation/ipv6.md) |
| IR | 9 | [IR allocation](allocation/ir.md) |
| LIFE | 14 | [LIFE allocation](allocation/life.md) |
| MGT | 15 | [MGT allocation](allocation/mgt.md) |
| MICRO | 5 | [MICRO allocation](allocation/micro.md) |
| MIG | 10 | [MIG allocation](allocation/mig.md) |
| MODEL | 13 | [MODEL allocation](allocation/model.md) |
| NSX | 3 | [NSX allocation](allocation/nsx.md) |
| NUT | 8 | [NUT allocation](allocation/nut.md) |
| OBS | 13 | [OBS allocation](allocation/obs.md) |
| ONB | 1 | [ONB allocation](allocation/onb.md) |
| OPS | 11 | [OPS allocation](allocation/ops.md) |
| OS | 5 | [OS allocation](allocation/os.md) |
| OVL | 5 | [OVL allocation](allocation/ovl.md) |
| PLACE | 7 | [PLACE allocation](allocation/place.md) |
| POL | 2 | [POL allocation](allocation/pol.md) |
| PORT | 3 | [PORT allocation](allocation/port.md) |
| QUAL | 3 | [QUAL allocation](allocation/qual.md) |
| REC | 16 | [REC allocation](allocation/rec.md) |
| REF | 2 | [REF allocation](allocation/ref.md) |
| REL | 6 | [REL allocation](allocation/rel.md) |
| RESP | 3 | [RESP allocation](allocation/resp.md) |
| RTE | 16 | [RTE allocation](allocation/rte.md) |
| SCOPE | 1 | [SCOPE allocation](allocation/scope.md) |
| SDI | 6 | [SDI allocation](allocation/sdi.md) |
| SEC | 9 | [SEC allocation](allocation/sec.md) |
| SITE | 8 | [SITE allocation](allocation/site.md) |
| STATE | 18 | [STATE allocation](allocation/state.md) |
| STD | 6 | [STD allocation](allocation/std.md) |
| STO | 5 | [STO allocation](allocation/sto.md) |
| SUP | 1 | [SUP allocation](allocation/sup.md) |
| SVC | 5 | [SVC allocation](allocation/svc.md) |
| SVCM | 2 | [SVCM allocation](allocation/svcm.md) |
| TEN | 9 | [TEN allocation](allocation/ten.md) |
| TEST | 10 | [TEST allocation](allocation/test.md) |
| TF | 18 | [TF allocation](allocation/tf.md) |
| THR | 1 | [THR allocation](allocation/thr.md) |
| VULN | 4 | [VULN allocation](allocation/vuln.md) |
| WSD | 13 | [WSD allocation](allocation/wsd.md) |
| ZIP | 21 | [ZIP allocation](allocation/zip.md) |
| ZONE | 6 | [ZONE allocation](allocation/zone.md) |

[Machine-readable allocation](../../sources/assurance/implementation_assertions.json) · [Editable CSV](../../sources/assurance/implementation_assertions.csv) · [Verification families](../assurance/verification-families.md)

No actual site, supported vendor tuple, native approval or complete implementation is invented. The enforced-state evidence class remains **NATIVE_NOT_RUN** even where a candidate function is exercised in a local fixture.

The JSON/CSV allocation is a proposed starting record for owner review. The one-time initializer refuses to overwrite an existing allocation. Maintain accepted owner, applicability and evidence assignments through a reviewed record change; `build_assurance_indexes.py` only republishes those records. Native evidence transitions require extending the acceptance checker deliberately and supplying actual evidence, not deleting its not-run guard.
