<?php

declare(strict_types=1);

namespace App\Application\Support\Actions;

use App\Application\Identity\Data\FederatedIdentity;
use App\Application\Tenancy\Actions\AuthorizeTenant;
use App\Domain\Identity\IdentityDenied;
use App\Domain\Support\SupportExpiry;
use App\Domain\Support\SupportLedger;
use App\Domain\Support\SupportPolicy;
use App\Domain\Support\SupportTrustState;
use App\Domain\Tenancy\GovernanceLedger;
use Illuminate\Support\Carbon;
use Illuminate\Support\Facades\DB;
use stdClass;

final class DecideSupportAccess
{
    public function __construct(private readonly SupportTransaction $transaction, private readonly SupportAuthority $authority, private readonly SupportValidity $validity) {}

    /** @param array<string, mixed> $input
     * @return array<string, mixed>
     */
    public function handle(#[\SensitiveParameter] string $token, #[\SensitiveParameter] string $workload, string $tenant, string $id, string $operation, string $key, array $input): array
    {
        return $this->transaction->handle($token, $workload, in_array($operation, ['approve', 'review'], true), function (FederatedIdentity $actor, ?SupportTrustState $trust) use ($token, $tenant, $id, $operation, $key, $input): array|IdentityDenied {
            $row = $this->transaction->request($actor, $tenant, $id);

            return $this->transaction->audited($row, $actor, $operation, function () use ($row, $actor, $trust, $token, $operation, $key, $input): array {
                $binding = json_decode($row->binding_json, true, 32, JSON_THROW_ON_ERROR);
                if (! hash_equals($row->binding_sha256, $input['binding_sha256'])) {
                    throw new IdentityDenied('support_binding_mismatch', 403);
                }
                $role = $input['role'] ?? null;
                if ($operation === 'revoke' && in_array($actor->subject, [$row->requester_id, $row->executor_id], true)) {
                    $approvalAuthority = null;
                } elseif ($operation === 'review') {
                    $approvalAuthority = $this->authority->security($actor->subject, $row->tenant_id, $binding, 'reviewer');
                    if ($trust === null) {
                        throw new IdentityDenied('support_trust_unavailable', 503);
                    }
                    $this->authority->session(hash('sha256', $token), $actor->subject, $trust, true);
                } elseif ($role === 'tenant') {
                    $approvalAuthority = $this->authority->membership($actor->subject, $row->tenant_id, $binding, true);
                } elseif ($role === 'security') {
                    $approvalAuthority = $this->authority->security($actor->subject, $row->tenant_id, $binding, 'approver');
                } else {
                    throw new IdentityDenied('forbidden', 403);
                }
                if (in_array($operation, ['approve', 'reject', 'review'], true)
                    && (in_array($actor->subject, [$row->requester_id, $row->executor_id], true)
                        || DB::table('app.support_approvals')->where('request_id', $row->id)->where('actor_id', $actor->subject)
                            ->when($operation !== 'review', fn ($query) => $query->where('role', '<>', $role))->exists())) {
                    throw new IdentityDenied('independent_approver_required', 403);
                }
                if ($operation === 'approve') {
                    if ($trust === null) {
                        throw new IdentityDenied('support_trust_unavailable', 503);
                    }
                    $this->validity->handle($row, $trust);
                    $this->authority->session(hash('sha256', $token), $actor->subject, $trust, true);
                }

                return $this->transaction->receipt($row->tenant_id, $actor->subject, 'support.'.$operation, $key, $input + ['request_id' => $row->id], function () use ($row, $actor, $trust, $token, $operation, $input, $role, $approvalAuthority, $binding): array {
                    if ($row->revision !== $input['revision']) {
                        throw new IdentityDenied('revision_conflict', 409);
                    }
                    if ($operation === 'review') {
                        return $this->review($row, $actor, $approvalAuthority, $input);
                    }
                    if (in_array($row->state, SupportPolicy::TERMINAL, true)
                        || (in_array($operation, ['approve', 'reject'], true) && $row->state !== 'requested')) {
                        throw new IdentityDenied('support_not_effective', 409);
                    }
                    if ($operation === 'approve') {
                        if ($trust === null || $approvalAuthority === null || ! in_array($role, ['tenant', 'security'], true)) {
                            throw new IdentityDenied('forbidden', 403);
                        }
                        if (DB::table('app.support_approvals')->where('request_id', $row->id)->where('role', $role)->exists()) {
                            throw new IdentityDenied('support_role_already_approved', 409);
                        }
                        $session = $this->authority->session(hash('sha256', $token), $actor->subject, $trust, true);
                        $expires = Carbon::parse($row->expires_at)->min(Carbon::parse($session->expires_at));
                        if ($approvalAuthority->expires_at !== null) {
                            $expires = $expires->min(Carbon::parse($approvalAuthority->expires_at));
                        }
                        $resources = GovernanceLedger::digest(['resources' => $this->authority->resources($row->tenant_id, $binding)]);
                        DB::table('app.support_approvals')->insert(['request_id' => $row->id, 'role' => $role, 'actor_id' => $actor->subject,
                            'authority_sha256' => $role === 'tenant' ? AuthorizeTenant::fingerprint($approvalAuthority) : SupportAuthority::securityFingerprint($approvalAuthority),
                            'resources_sha256' => $resources, 'security_grant_id' => $role === 'security' ? $approvalAuthority->id : null,
                            'session_hash' => hash('sha256', $token), 'expires_at' => $expires, 'created_at' => now()]);
                        $row->revision++;
                        $row->state = DB::table('app.support_approvals')->where('request_id', $row->id)->count() === 2 ? 'approved' : 'requested';
                        DB::table('app.support_requests')->where('id', $row->id)->update(['state' => $row->state, 'revision' => $row->revision]);
                        SupportLedger::record($row->tenant_id, $actor->subject, 'support.access.approved', $row->id, $row->revision,
                            ['binding_sha256' => $row->binding_sha256, 'role' => $role, 'resources_sha256' => $resources,
                                'effective_until' => $expires->toIso8601String(), 'case_reference' => $binding['case_reference']]);
                    } elseif ($operation === 'reject' || $operation === 'revoke') {
                        SupportExpiry::end($row, $operation === 'reject' ? 'rejected' : 'revoked', $actor->subject,
                            ['reason_code' => $input['reason_code'], 'case_reference' => $input['case_reference']]);
                    } else {
                        throw new IdentityDenied('forbidden', 403);
                    }

                    return ['id' => $row->id, 'state' => $row->state, 'revision' => $row->revision,
                        'binding_sha256' => $row->binding_sha256, 'authority_use' => 'request_status_only'];
                });
            });
        }, $tenant, $id);
    }

    /** @param array<string, mixed> $input
     * @return array<string, mixed>
     */
    private function review(stdClass $row, FederatedIdentity $actor, ?stdClass $grant, array $input): array
    {
        if ($grant === null || ! in_array($row->state, SupportPolicy::TERMINAL, true) || $row->admission_count === 0) {
            throw new IdentityDenied('support_review_not_due', 409);
        }
        if (DB::table('app.support_reviews')->where('request_id', $row->id)->exists()) {
            throw new IdentityDenied('support_already_reviewed', 409);
        }
        DB::table('app.support_reviews')->insert(['request_id' => $row->id, 'actor_id' => $actor->subject,
            'security_grant_id' => $grant->id, 'outcome' => $input['outcome'], 'case_reference' => $input['case_reference'], 'reviewed_at' => now()]);
        SupportLedger::record($row->tenant_id, $actor->subject, 'support.access.reviewed', $row->id, $row->revision,
            ['binding_sha256' => $row->binding_sha256, 'outcome' => $input['outcome'], 'case_reference' => $input['case_reference']]);

        return ['id' => $row->id, 'reviewed' => true, 'outcome' => $input['outcome'], 'authority_use' => 'request_status_only'];
    }
}
