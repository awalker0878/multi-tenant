# NSX gateway quarantine

Owns one scoped, logged Emergency gateway DROP policy. The existing gateway must
actually provide stateful gateway enforcement in its accepted topology. This module
does not create T0/T1/VRF/Edge interfaces, enable a firewall, manage precedence or
prove that distributed paths traverse it. No ALLOW is emitted. It complements,
rather than replaces, the existing disconnected segment and domain policy.

The global/site security owner reserves the sequence and controls who can edit it.
`locked=false` avoids asserting an object lock is RBAC or making later owned changes
unmanageable. Native roles, exclusions, existing earlier policies, release support
and realised packet paths need inspection and native tests before reliance.

Use only a separately accepted restricted scope. Removing the module's code also
removes the protection offered by prevent_destroy; access controls and disposal
approval remain required. Provider plan tests supplied here are not run.
