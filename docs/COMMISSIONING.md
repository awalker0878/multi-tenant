# Increment04 commissioning and recovery hold points

1. **Toolchain gate.** Validate all retained candidate modules with a verified
   Terraform binary and trusted provider packages on an approved connected runner.
   Current package results remain blocked at this gate; no native apply here.
2. **Target and owner gate.** Select the installed platform/API/provider combination,
   exact disposable scope, management origin, trust roots and resource owner. Grant
   the new collectors only the required read privilege. No discovery is implied.
3. **Independent expectation.** Record the accepted resource paths, complete selected
   fields and version/ETag/intent/task bindings. Read-response defaults must not
   replace an engineering decision. Resolve missing/optional representations before use.
4. **Restricted observation.** Validate inputs without contact, then use an explicit
   read flag, matching origin, injected credentials and a new private output.
   Preserve denied-domain/workload posture and current incident controls.
5. **Interrupted-change control.** Establish true writer ownership/fencing and
   quarantine. Collect and review current native state before proposing a replay,
   cancellation, import, replacement or data disposal. The offline reviewer never
   authorizes or performs those actions.
6. **Independent verification.** Check actual routing/enforcement, placement, storage,
   identity, DNS/protection and operating dependencies. Aggregate native success is
   only one evidence input. Include the authorized changed-path and failure tests.
7. **Service acceptance.** The required initial operational/recovery readiness must
   precede production activation. No command in this increment releases quarantine
   or marks a workload authorized for production.

[Native reader details](NATIVE_READBACK.md) ·
[Recovery decisions](INTERRUPTED_CHANGE_RECOVERY.md) ·
[Retained DNS lifecycle](DNS_LIFECYCLE.md) ·
[Retained service-identity fixture](SERVICE_IDENTITY.md)
