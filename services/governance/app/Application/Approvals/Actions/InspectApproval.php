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
use App\Domain\Tenancy\GovernanceLedger;
use Illuminate\Support\Facades\DB;

final class InspectApproval
{
    public function __construct(private readonly AuthorizeTenant $authority, private readonly ImmutablePlanSource $plans) {}

    /** @param array<string, mixed>|null $binding
     * @return array<string, mixed>
     */
    public function handle(#[\SensitiveParameter] string $token, string $tenant, string $id, ?array $binding = null): array
    {
        $result = DB::transaction(function () use ($token, $tenant, $id, $binding): array|IdentityDenied {
            BootstrapAdministrator::query()->lockForUpdate()->findOrFail(1);
            $actor = $this->authority->actor($token);
            $this->authority->handle($actor, $tenant, 'tenant.read');
            $approval = DB::table('app.approvals')->where('tenant_id', $tenant)->where('id', $id)->lockForUpdate()->first();
            if ($approval === null) {
                throw new IdentityDenied('not_found', 404);
            }
            $plan = BoundPlan::fromArray(json_decode($approval->binding_json, true, 32, JSON_THROW_ON_ERROR));
            $this->authority->handle($actor, $tenant, $binding === null ? 'plan.read' : 'operation.admit', $plan->scope());
            ApprovalExpiry::apply($approval);
            $projection = ['id' => $id, 'state' => $approval->state, 'revision' => $approval->revision, 'binding' => $plan->toArray(),
                'requester_id' => $approval->requester_id, 'decided_by' => $approval->decided_by, 'expires_at' => $approval->expires_at];
            if ($binding === null) {
                return $projection;
            }
            if ($approval->state !== 'approved') {
                return new IdentityDenied('approval_not_effective', 409);
            }
            $expected = ['plan_id' => $approval->plan_id, 'plan_revision' => $approval->plan_revision, 'plan_digest' => $plan->digest,
                'action' => $plan->binding['action'], 'scope' => $plan->scope()];
            if (! hash_equals(GovernanceLedger::digest($expected), GovernanceLedger::digest($binding)) || ! in_array($actor->subject, $plan->binding['executor_ids'], true)) {
                return new IdentityDenied('approval_binding_mismatch', 403);
            }
            $current = BoundPlan::fromArray($this->plans->fetch($approval->plan_id, $approval->plan_revision));
            if (! hash_equals($current->digest, $plan->digest)) {
                return new IdentityDenied('plan_binding_changed', 409);
            }
            // Membership/grant revocation prevents new use even with a historical approval.
            $requestAuthority = $this->authority->handle(new FederatedIdentity($approval->requester_id, false), $tenant, 'approval.request', $plan->scope());
            $decisionAuthority = $this->authority->handle(new FederatedIdentity($approval->decided_by, false), $tenant, 'approval.decide', $plan->scope());
            if (! hash_equals($approval->request_authority, AuthorizeTenant::fingerprint($requestAuthority))
                || ! hash_equals($approval->decision_authority, AuthorizeTenant::fingerprint($decisionAuthority))) {
                return new IdentityDenied('approval_authority_changed', 403);
            }

            return ['allowed' => true, 'approval_id' => $id, 'approval_revision' => $approval->revision, 'actor_id' => $actor->subject,
                'tenant_id' => $tenant, 'plan_digest' => $plan->digest, 'authority_use' => 'observation_only'];
        });
        if ($result instanceof IdentityDenied) {
            throw $result;
        }

        return $result;
    }
}
