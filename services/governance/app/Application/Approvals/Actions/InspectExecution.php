<?php

declare(strict_types=1);

namespace App\Application\Approvals\Actions;

use App\Application\Approvals\Contracts\ImmutablePlanSource;
use App\Application\Identity\Data\FederatedIdentity;
use App\Application\Tenancy\Actions\AuthorizeTenant;
use App\Domain\Approvals\ApprovalExpiry;
use App\Domain\Approvals\BoundPlan;
use App\Domain\Identity\BootstrapAdministrator;
use App\Domain\Identity\IdentityDenied;
use Illuminate\Support\Carbon;
use Illuminate\Support\Facades\DB;

final class InspectExecution
{
    public function __construct(private readonly AuthorizeTenant $authority, private readonly ImmutablePlanSource $plans) {}

    /** @param array<string, mixed> $input
     * @return array<string, mixed> */
    public function handle(string $tenant, array $input): array
    {
        return $this->inspect($tenant, $input, false);
    }

    /** An approval is one input to native admission, never a platform write grant.
     * @param array<string, mixed> $input
     * @return array<string, mixed> */
    public function native(string $tenant, array $input): array
    {
        return $this->inspect($tenant, $input, true);
    }

    /** @param array<string, mixed> $input
     * @return array<string, mixed> */
    private function inspect(string $tenant, array $input, bool $native): array
    {
        return DB::transaction(function () use ($tenant, $input, $native): array {
            BootstrapAdministrator::query()->lockForUpdate()->findOrFail(1);
            $actor = DB::table('app.federated_actors as a')->join('app.oidc_connections as c', 'c.issuer', '=', 'a.issuer')
                ->join('app.oidc_installation as i', 'i.active_revision', '=', 'c.revision')
                ->where('i.id', 1)->where('a.id', $input['actor_id'])->whereNull('a.disabled_at')->first(['a.id']);
            if ($actor === null) {
                throw new IdentityDenied('executor_not_current', 403);
            }
            $approval = DB::table('app.approvals')->where('tenant_id', $tenant)->where('id', $input['approval_id'])->lockForUpdate()->first();
            if ($approval === null) {
                throw new IdentityDenied('not_found', 404);
            }
            $plan = BoundPlan::fromArray(json_decode($approval->binding_json, true, 32, JSON_THROW_ON_ERROR));
            ApprovalExpiry::apply($approval);
            if ($approval->state !== 'approved' || ($plan->binding['lane'] ?? null) !== ($native ? 'operational' : 'isolated_campaign')
                || $plan->binding['valid_until'] <= now()->getTimestamp()
                || $approval->plan_id !== $input['plan_id'] || $approval->plan_revision !== $input['plan_revision']
                || ! hash_equals($plan->digest, $input['plan_digest'])
                || ! in_array($actor->id, $plan->binding['executor_ids'], true)
                || in_array($approval->decided_by, [$actor->id, $approval->requester_id], true)) {
                throw new IdentityDenied('execution_binding_denied', 403);
            }
            $executor = $this->authority->handle(new FederatedIdentity($actor->id, false), $tenant, 'operation.admit', $plan->scope());
            $requester = $this->authority->handle(new FederatedIdentity($approval->requester_id, false), $tenant, 'approval.request', $plan->scope());
            $reviewer = $this->authority->handle(new FederatedIdentity($approval->decided_by, false), $tenant, 'approval.decide', $plan->scope());
            if (! hash_equals($approval->request_authority, AuthorizeTenant::fingerprint($requester))
                || ! hash_equals($approval->decision_authority, AuthorizeTenant::fingerprint($reviewer))
                || ! hash_equals($plan->digest, BoundPlan::fromArray($this->plans->fetch($approval->plan_id, $approval->plan_revision))->digest)) {
                throw new IdentityDenied('approval_authority_changed', 403);
            }

            $result = ['allowed' => true, 'tenant_id' => $tenant, 'actor_id' => $actor->id, 'approval_id' => $approval->id,
                'plan_digest' => $plan->digest, 'executor_fingerprint' => AuthorizeTenant::fingerprint($executor),
                'authority_use' => $native ? 'native_approval' : 'simulation_boundary', 'evaluated_at' => now()->getTimestamp(),
                'approval' => ['state' => 'approved', 'revoked' => false, 'plan_digest' => $plan->digest,
                    'plan_id' => $approval->plan_id, 'plan_revision' => $approval->plan_revision,
                    'approver_id' => $approval->decided_by, 'approver_grant_current' => true,
                    'expires_at' => Carbon::parse($approval->expires_at)->getTimestamp(), 'scope' => $plan->scope()],
                'native_write_authorized' => false];
            if ($native) {
                $result['requester_id'] = $approval->requester_id;
            }

            return $result;
        });
    }
}
