<?php

declare(strict_types=1);

namespace App\Application\Tenancy\Actions;

use App\Application\Identity\Data\FederatedIdentity;
use App\Domain\Identity\BootstrapAdministrator;
use App\Domain\Identity\IdentityDenied;
use App\Domain\Tenancy\GovernanceLedger;
use Closure;
use Illuminate\Support\Facades\DB;

final class ExecuteGovernanceCommand
{
    public function __construct(private readonly AuthorizeTenant $authority) {}

    /** @param array<string, mixed> $payload
     * @param  Closure(FederatedIdentity): array<string, mixed>  $execute
     * @param  array{site_id?: string|null, environment?: string|null, resource_id?: string|null}  $scope
     * @return array<string, mixed>
     */
    public function handle(#[\SensitiveParameter] string $token, ?string $tenant, string $permission, string $command, string $key, array $payload, Closure $execute, array $scope = []): array
    {
        return DB::transaction(function () use ($token, $tenant, $permission, $command, $key, $payload, $execute, $scope): array {
            // One lock order also serializes activation/revocation with command admission.
            BootstrapAdministrator::query()->lockForUpdate()->findOrFail(1);
            $actor = $this->authority->actor($token);
            if ($tenant === null) {
                if (! $actor->installationAdministrator || $permission !== 'tenants.create') {
                    throw new IdentityDenied('forbidden', 403);
                }
            } else {
                DB::table('app.tenants')->where('id', $tenant)->lockForUpdate()->first();
                $this->authority->handle($actor, $tenant, $permission, $scope);
            }
            // Current authority is checked even when returning a previous command receipt.
            $receiptQuery = DB::table('app.governance_commands')->where('scope_id', $tenant ?? 'installation')
                ->where('actor_id', $actor->subject)->where('command', $command)->where('request_key', $key);
            $digest = GovernanceLedger::digest($payload);
            $receipt = $receiptQuery->first();
            if ($receipt !== null) {
                if (! hash_equals($receipt->digest, $digest)) {
                    throw new IdentityDenied('idempotency_conflict', 409);
                }

                return json_decode($receipt->result_json, true, 32, JSON_THROW_ON_ERROR);
            }
            $result = $execute($actor);
            DB::table('app.governance_commands')->insert([
                'scope_id' => $tenant ?? 'installation', 'actor_id' => $actor->subject, 'command' => $command,
                'request_key' => $key, 'digest' => $digest, 'result_json' => json_encode($result, JSON_THROW_ON_ERROR), 'created_at' => now(),
            ]);

            return $result;
        });
    }
}
