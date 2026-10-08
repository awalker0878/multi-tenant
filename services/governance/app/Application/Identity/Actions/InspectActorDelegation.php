<?php

declare(strict_types=1);

namespace App\Application\Identity\Actions;

use App\Application\Identity\Contracts\ServiceCredentials;
use App\Application\Identity\Data\FederatedIdentity;
use App\Application\Tenancy\Actions\AuthorizeTenant;
use App\Domain\Identity\BootstrapAdministrator;
use App\Domain\Identity\DelegationPolicy;
use App\Domain\Identity\IdentityDenied;
use App\Domain\Tenancy\GovernanceLedger;
use Illuminate\Support\Facades\DB;

final class InspectActorDelegation
{
    public function __construct(private readonly AuthorizeTenant $authority, private readonly ServiceCredentials $credentials, private readonly CheckIdentityAdmission $admission) {}

    /** @param array{site_id: ?string, environment: ?string, resource_id: ?string} $scope
     * @return array<string, mixed>
     */
    public function handle(string $audience, #[\SensitiveParameter] string $token, string $tenant, string $action, array $scope): array
    {
        $this->admission->handle();

        return DB::transaction(function () use ($audience, $token, $tenant, $action, $scope): array {
            BootstrapAdministrator::query()->lockForUpdate()->findOrFail(1);
            if (! preg_match('/\A[0-9a-f]{64}\z/', $token)) {
                throw new IdentityDenied('invalid_delegation');
            }
            $grant = DB::table('app.actor_delegations as d')
                ->join('app.federated_sessions as s', 's.token_hash', '=', 'd.session_hash')
                ->join('app.federated_actors as a', 'a.id', '=', 'd.actor_id')
                ->join('app.oidc_installation as i', 'i.active_revision', '=', 's.connection_revision')
                ->join('app.oidc_connections as c', 'c.revision', '=', 'i.active_revision')
                ->where('d.token_hash', hash('sha256', $token))->where('d.audience', $audience)
                ->where('d.tenant_id', $tenant)->where('d.action', $action)->where('i.id', 1)
                ->where('s.audience', 'console')->whereColumn('a.issuer', 'c.issuer')->whereColumn('s.actor_id', 'd.actor_id')
                ->whereNull('d.revoked_at')->whereNull('s.revoked_at')->whereNull('a.disabled_at')
                ->where('d.expires_at', '>', now())->where('s.expires_at', '>', now())->first(['d.*']);
            if ($grant === null || ! DelegationPolicy::permits($audience, $action)
                || ! hash_equals(GovernanceLedger::digest(json_decode($grant->scope_json, true, 8, JSON_THROW_ON_ERROR)), GovernanceLedger::digest($scope))
                || ! hash_equals($grant->service_fingerprint, $this->credentials->fingerprint($audience))
                || ! hash_equals($grant->console_fingerprint, $this->credentials->fingerprint('console'))) {
                throw new IdentityDenied('invalid_delegation');
            }
            $membership = $this->authority->handle(new FederatedIdentity($grant->actor_id, false), $tenant, $action, $scope);
            if (! hash_equals($grant->authority_fingerprint, AuthorizeTenant::fingerprint($membership))) {
                throw new IdentityDenied('invalid_delegation');
            }

            return ['allowed' => true, 'delegation_id' => $grant->id, 'actor_id' => $grant->actor_id,
                'delegating_service' => 'console', 'audience' => $audience, 'tenant_id' => $tenant,
                'action' => $action, 'scope' => $scope, 'expires_at' => $grant->expires_at,
                'evaluated_at' => now()->toIso8601String(), 'authority_use' => 'request_bound'];
        });
    }
}
