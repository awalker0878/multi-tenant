<?php

declare(strict_types=1);

namespace App\Application\Approvals\Actions;

use App\Application\Approvals\Contracts\ImmutablePlanSource;
use App\Application\Identity\Data\FederatedIdentity;
use App\Application\Tenancy\Actions\AuthorizeTenant;
use App\Application\Tenancy\Actions\ExecuteGovernanceCommand;
use App\Domain\Approvals\BoundPlan;
use App\Domain\Identity\IdentityDenied;
use App\Domain\Tenancy\GovernanceLedger;
use Illuminate\Support\Carbon;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Str;

final class ManageApproval
{
    public function __construct(private readonly AuthorizeTenant $authority, private readonly ExecuteGovernanceCommand $commands, private readonly ImmutablePlanSource $plans) {}

    /** @param array<string, mixed> $input
     * @return array<string, mixed>
     */
    public function handle(#[\SensitiveParameter] string $token, string $tenant, string $operation, string $key, array $input): array
    {
        $actor = $this->authority->actor($token);
        $this->authority->handle($actor, $tenant, 'tenant.read');
        if ($operation === 'request') {
            $plan = $this->fetch($input['plan_id'], $input['plan_revision'], $input['plan_digest']);
            if ($plan->binding['tenant_id'] !== $tenant) {
                throw new IdentityDenied('not_found', 404);
            }

            return $this->commands->handle($token, $tenant, 'approval.request', 'approval.request', $key, $input,
                fn (FederatedIdentity $current): array => $this->request($current, $tenant, $plan, $input), $plan->scope());
        }
        $approval = DB::table('app.approvals')->where('tenant_id', $tenant)->where('id', $input['approval_id'])->first();
        if ($approval === null) {
            throw new IdentityDenied('not_found', 404);
        }
        $plan = BoundPlan::fromArray(json_decode($approval->binding_json, true, 32, JSON_THROW_ON_ERROR));
        $permission = $operation === 'revoke' ? 'approval.revoke' : 'approval.decide';

        return $this->commands->handle($token, $tenant, $permission, 'approval.'.$operation, $key, $input,
            function (FederatedIdentity $current) use ($tenant, $operation, $input, $plan): array {
                $approval = DB::table('app.approvals')->where('tenant_id', $tenant)->where('id', $input['approval_id'])->lockForUpdate()->first();
                if ($approval === null || $approval->revision !== $input['revision']) {
                    throw new IdentityDenied('revision_conflict', 409);
                }
                if (Carbon::parse($approval->expires_at)->isPast() || $plan->binding['valid_until'] <= now()->getTimestamp()) {
                    throw new IdentityDenied('approval_expired', 409);
                }
                if (($operation === 'revoke' && $approval->state !== 'approved') || ($operation !== 'revoke' && $approval->state !== 'requested')) {
                    throw new IdentityDenied('invalid_approval_transition', 409);
                }
                if ($operation !== 'revoke' && ($current->subject === $approval->requester_id || in_array($current->subject, $plan->binding['executor_ids'], true))) {
                    throw new IdentityDenied('independent_approver_required', 403);
                }
                if ($operation === 'approve') {
                    $this->fetch($approval->plan_id, $approval->plan_revision, $approval->plan_digest);
                }
                $state = match ($operation) {
                    'approve' => 'approved', 'reject' => 'rejected', 'revoke' => 'revoked', default => throw new IdentityDenied('forbidden', 403)
                };
                $revision = $approval->revision + 1;
                $authority = $this->authority->handle($current, $tenant, $operation === 'revoke' ? 'approval.revoke' : 'approval.decide', $plan->scope());
                DB::table('app.approvals')->where('tenant_id', $tenant)->where('id', $approval->id)->update([
                    'state' => $state, 'revision' => $revision, 'decided_by' => $operation === 'revoke' ? $approval->decided_by : $current->subject,
                    'decision_authority' => $operation === 'revoke' ? $approval->decision_authority : AuthorizeTenant::fingerprint($authority),
                ]);
                $result = ['id' => $approval->id, 'state' => $state, 'revision' => $revision, 'plan_digest' => $plan->digest];
                GovernanceLedger::record($tenant, $current->subject, 'governance.approval.'.$state, $approval->id, $revision, $result + ['reason' => $input['reason']]);

                return $result;
            }, $plan->scope());
    }

    /** @param array<string, mixed> $input
     * @return array<string, mixed>
     */
    private function request(FederatedIdentity $actor, string $tenant, BoundPlan $plan, array $input): array
    {
        $expires = Carbon::parse($input['expires_at']);
        if ($plan->binding['requested_by'] !== $actor->subject) {
            throw new IdentityDenied('wrong_plan_actor', 403);
        }
        if ($expires->isPast() || $expires->greaterThan(now()->addDay()) || $expires->getTimestamp() > $plan->binding['valid_until']) {
            throw new IdentityDenied('invalid_approval_expiry', 422);
        }
        $id = (string) Str::uuid();
        DB::table('app.approvals')->insert(['id' => $id, 'tenant_id' => $tenant, 'plan_id' => $plan->binding['plan_id'],
            'plan_revision' => $plan->binding['revision'], 'plan_digest' => $plan->digest, 'binding_json' => json_encode($plan->toArray(), JSON_THROW_ON_ERROR),
            'requester_id' => $actor->subject, 'state' => 'requested', 'revision' => 1, 'expires_at' => $expires, 'created_at' => now(),
            'request_authority' => AuthorizeTenant::fingerprint($this->authority->handle($actor, $tenant, 'approval.request', $plan->scope()))]);
        $result = ['id' => $id, 'state' => 'requested', 'revision' => 1, 'plan_digest' => $plan->digest, 'expires_at' => $expires->toIso8601String()];
        GovernanceLedger::record($tenant, $actor->subject, 'governance.approval.requested', $id, 1, $result + ['binding' => $plan->toArray()]);

        return $result;
    }

    private function fetch(string $id, int $revision, string $digest): BoundPlan
    {
        $plan = BoundPlan::fromArray($this->plans->fetch($id, $revision));
        if ($plan->binding['plan_id'] !== $id || $plan->binding['revision'] !== $revision || ! hash_equals($plan->digest, $digest)
            || $plan->binding['valid_until'] <= now()->getTimestamp()) {
            throw new IdentityDenied('plan_binding_changed', 409);
        }

        return $plan;
    }
}
