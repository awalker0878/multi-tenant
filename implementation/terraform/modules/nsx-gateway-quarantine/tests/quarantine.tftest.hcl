mock_provider "nsxt" {}
run "scoped_drop_plan" {
 command = plan
 variables {
  tenant_key = "tenant-01"
  domain_key = "D01O"
  allow_restricted_build = true
  test_authorization_ref = "MOCK-test_authorization_ref"
  engineering_record_ref = "MOCK-engineering_record_ref"
  attachment_acceptance_ref = "MOCK-attachment_acceptance_ref"
  gateway_path = "/infra/tier-0s/mock-isolated"
  quarantine_sequence = 10
 }
 assert {
 condition = nsxt_policy_gateway_policy.owned.stateful == true
 error_message = "Quarantine must remain stateful."
 }
}
