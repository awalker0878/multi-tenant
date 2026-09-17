# Implementation work

Use [commissioning](../COMMISSIONING.md), [native readback](../NATIVE_READBACK.md),
[DNS lifecycle](../DNS_LIFECYCLE.md), [interrupted-change recovery](../INTERRUPTED_CHANGE_RECOVERY.md)
and [testing](../TESTING.md) with the accepted engineering release.

The [implementation kit](../../reference/Portable_Hosting_Delivery_Kits_v1_1/03_Implementation/Implementation_Kit.docx),
[method/test/handover template](../../reference/Portable_Hosting_Delivery_Kits_v1_1/03_Implementation/MOP_Test_and_Handover_Template.docx),
[qualification procedures](../../reference/Portable_Hosting_Delivery_Kits_v1_1/03_Implementation/Qualification_Campaign_and_Evidence_Procedures.docx)
and [operations playbook](../../reference/Portable_Hosting_Delivery_Kits_v1_1/03_Implementation/Operations_Recovery_and_Transition_Playbook.docx)
remain the supplied working documents.

Current native implementations are [Terraform](../../terraform/README.md) and the
existing tools. [Ansible](../../ansible/README.md) adds separate local staging and
validation; no production apply workflow is included. Initial operational/recovery
readiness remains required before production activation. Native platform tests and
approval are not issued by source, mocks or repository CI.
