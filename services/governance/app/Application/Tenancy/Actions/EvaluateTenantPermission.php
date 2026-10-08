<?php

declare(strict_types=1);

namespace App\Application\Tenancy\Actions;

use App\Domain\Identity\BootstrapAdministrator;
use Illuminate\Support\Facades\DB;

final class EvaluateTenantPermission
{
    public function __construct(private readonly AuthorizeTenant $authority) {}

    /** @param array{site_id?: string|null, environment?: string|null, resource_id?: string|null} $scope
     * @return array<string, mixed>
     */
    public function handle(#[\SensitiveParameter] string $token, string $tenant, string $action, array $scope): array
    {
        return DB::transaction(function () use ($token, $tenant, $action, $scope): array {
            BootstrapAdministrator::query()->lockForUpdate()->findOrFail(1);
            $actor = $this->authority->actor($token);
            $member = $this->authority->handle($actor, $tenant, $action, $scope);

            return ['allowed' => true, 'actor_id' => $actor->subject, 'tenant_id' => $tenant,
                'action' => $action, 'scope' => $scope, 'membership_revision' => $member->revision,
                'evaluated_at' => now()->toIso8601String(), 'authority_use' => 'observation_only'];
        });
    }
}
