/** Resolution guidance only; the inventory and planning owners decide eligibility. */
export function migrationHold(reason: string): string {
  const guidance: Record<string, string> = {
    source_enrollment_unavailable: 'Ask the environment administrator to restore the approved source connection.',
    source_inventory_expired: 'Refresh the source connection from its API, then review the new observations.',
    source_absent_or_generation_changed: 'Refresh source inventory and confirm the current VM identity before selecting it again.',
    source_profile_required: 'Enable workload profiles for the enrolled source scope and refresh from its API.',
    source_profile_stale: 'Refresh the source workload profile and confirm a new migration review.',
    source_identity_required: 'Ask the environment administrator to resolve the missing immutable source identity.',
    target_profile_stale: 'Refresh the destination profile and review its current capabilities.',
    target_format_unavailable: 'Choose an observed destination disk format and save the migration group.',
    group_source_identity_requires_review: 'Review the changed source identity and save this group again.',
    confirmed_vm_review_required: 'Open this VM’s readiness review, map every disk, supply the owner references and confirm it.',
    review_profile_pair_changed: 'Update this VM’s review to the exact source and destination profiles selected for the group.',
  };
  return `${reason.replaceAll('_', ' ')} — ${guidance[reason] ?? 'Review the original API observation and ask the responsible platform or application owner to resolve this requirement before confirmation.'}`;
}
