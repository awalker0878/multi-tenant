<?php

declare(strict_types=1);

namespace App\Application\Support\Actions;

use App\Application\Identity\Data\FederatedIdentity;
use App\Domain\Identity\IdentityDenied;
use App\Domain\Support\SupportLedger;
use App\Domain\Support\SupportPolicy;
use App\Domain\Support\SupportTrustState;
use Illuminate\Support\Carbon;
use Illuminate\Support\Facades\DB;

final class UseSupportAccess
{
    public function __construct(private readonly SupportTransaction $transaction, private readonly SupportAuthority $authority, private readonly SupportValidity $validity) {}

    /** @param array<string, mixed> $input
     * @return array<string, mixed>
     */
    public function handle(#[\SensitiveParameter] string $token, #[\SensitiveParameter] string $workload, string $tenant, string $id, string $operation, string $key, array $input): array
    {
        return $this->transaction->handle($token, $workload, true, function (FederatedIdentity $actor, ?SupportTrustState $trust) use ($token, $tenant, $id, $operation, $key, $input): array|IdentityDenied {
            $row = $this->transaction->request($actor, $tenant, $id);

            return $this->transaction->audited($row, $actor, $operation, function () use ($row, $actor, $trust, $token, $operation, $key, $input): array {
                if ($actor->subject !== $row->executor_id || ! hash_equals($row->binding_sha256, $input['binding_sha256'])) {
                    throw new IdentityDenied('support_binding_mismatch', 403);
                }
                if ($trust === null) {
                    throw new IdentityDenied('support_trust_unavailable', 503);
                }
                $binding = $this->validity->handle($row, $trust);
                $session = $this->authority->session(hash('sha256', $token), $actor->subject, $trust, $operation === 'activate');
                if (DB::table('app.support_approvals')->where('request_id', $row->id)->count() !== 2
                    || ! in_array($row->state, ['approved', 'active'], true)) {
                    throw new IdentityDenied('support_dual_approval_required', 403);
                }
                if ($operation === 'activate') {
                    if (DB::table('app.support_requests as requests')->leftJoin('app.support_reviews as reviews', 'reviews.request_id', '=', 'requests.id')
                        ->where('requests.executor_id', $actor->subject)->where('requests.admission_count', '>', 0)
                        ->where('requests.effective_until', '<=', now()->subHours(SupportPolicy::REVIEW_HOURS))->whereNull('reviews.request_id')->exists()) {
                        throw new IdentityDenied('support_review_required', 403);
                    }
                    if ($row->executor_session_hash !== null && ! hash_equals($row->executor_session_hash, hash('sha256', $token))) {
                        throw new IdentityDenied('support_session_mismatch', 403);
                    }

                    return $this->transaction->receipt($row->tenant_id, $actor->subject, 'support.activate', $key, $input + ['request_id' => $row->id], function () use ($row, $actor, $token, $session, $input): array {
                        if ($row->revision !== $input['revision'] || $row->state !== 'approved') {
                            throw new IdentityDenied('revision_conflict', 409);
                        }
                        $expires = Carbon::parse($row->expires_at)->min(Carbon::parse($session->expires_at));
                        foreach (DB::table('app.support_approvals')->where('request_id', $row->id)->get() as $approval) {
                            $expires = $expires->min(Carbon::parse($approval->expires_at));
                        }
                        DB::table('app.support_requests')->where('id', $row->id)->update(['state' => 'active', 'revision' => $row->revision + 1,
                            'executor_session_hash' => hash('sha256', $token), 'effective_until' => $expires]);
                        SupportLedger::record($row->tenant_id, $actor->subject, 'support.access.activated', $row->id, $row->revision + 1,
                            ['binding_sha256' => $row->binding_sha256, 'effective_until' => $expires->toIso8601String()]);

                        return ['id' => $row->id, 'state' => 'active', 'revision' => $row->revision + 1, 'effective_until' => $expires->toIso8601String(),
                            'binding_sha256' => $row->binding_sha256, 'authority_use' => 'request_status_only'];
                    });
                }
                if ($operation !== 'inspect' || $row->state !== 'active' || ! is_string($row->executor_session_hash)
                    || ! hash_equals($row->executor_session_hash, hash('sha256', $token))) {
                    throw new IdentityDenied('support_session_mismatch', 403);
                }
                if ($input['site_id'] !== $binding['site_id'] || $input['environment'] !== $binding['environment']
                    || ! in_array($input['action'], $binding['actions'], true)) {
                    throw new IdentityDenied('support_scope_mismatch', 403);
                }
                $kind = SupportPolicy::ACTIONS[$input['action']] ?? null;
                $resources = $this->authority->resources($row->tenant_id, $binding);
                $selected = array_values(array_filter($resources, static fn (array $resource): bool => $resource['kind'] === $kind && $resource['id'] === $input['resource_id']));
                if (count($selected) !== 1) {
                    throw new IdentityDenied('support_scope_mismatch', 403);
                }
                if ($row->admission_count >= 1000) {
                    throw new IdentityDenied('support_admission_limit', 429);
                }
                // Protected data is obtained and its admission fact committed under
                // the same owner lock. No reusable authorization token is returned.
                DB::table('app.support_requests')->where('id', $row->id)->update(['admission_count' => $row->admission_count + 1]);
                SupportLedger::record($row->tenant_id, $actor->subject, 'support.access.admitted', $row->id, $row->revision,
                    ['binding_sha256' => $row->binding_sha256, 'action' => $input['action'], 'resource_id' => $input['resource_id'],
                        'site_id' => $binding['site_id'], 'environment' => $binding['environment'], 'case_reference' => $binding['case_reference']]);

                return ['request_id' => $row->id, 'tenant_id' => $row->tenant_id, 'action' => $input['action'],
                    'resource' => $selected[0], 'authority_use' => 'diagnostic_result_only'];
            });
        }, $tenant, $id);
    }
}
