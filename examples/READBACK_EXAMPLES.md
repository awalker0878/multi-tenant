# Disabled native readback and recovery inputs

[NSX example](nsx_observation.json.example) and
[Nutanix example](nutanix_observation.json.example) illustrate exact selected-object
shape only. `contact_enabled` is false; endpoints end in `.invalid`; paths, UUIDs,
operation/version tokens and evidence references are invented documentation data.
The validators can inspect these files without contacting any service. Do not treat
them as actual target inventories, expected state or approval.

[Recovery context](recovery_context.json.example) deliberately has zero digests,
UNKNOWN executor/containment and unverified fence/quarantine records. It must not
satisfy recovery review. Use the independently controlled implementation records,
not this example, after a real interrupted operation.

The native expectation must be accepted independently of the readback being checked.
The same name or portable label does not establish native ownership. All additional
reads and mutations stay within their actual owner/tool and authorization scope.
