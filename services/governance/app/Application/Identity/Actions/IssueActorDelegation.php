<?php

declare(strict_types=1);

namespace App\Application\Identity\Actions;

use App\Application\Identity\Contracts\ServiceCredentials;
use App\Application\Tenancy\Actions\AuthorizeTenant;
use App\Domain\Identity\BootstrapAdministrator;
use App\Domain\Identity\DelegationPolicy;
use App\Domain\Identity\IdentityDenied;
use App\Domain\Identity\IdentityLedger;
use Illuminate\Support\Carbon;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Str;

final class IssueActorDelegation
{
    public function __construct(private readonly AuthorizeTenant $authority, private readonly ServiceCredentials $credentials) {}

    /** @param array{site_id: ?string, environment: ?string, resource_id: ?string} $scope
     * @return array<string, mixed>
     */
    public function handle(#[\SensitiveParameter] string $session, string $tenant, string $audience, string $action, array $scope): array
    {
        return DB::transaction(function () use ($session, $tenant, $audience, $action, $scope): array {
            BootstrapAdministrator::query()->lockForUpdate()->findOrFail(1);
            $actor = $this->authority->actor($session);
            if (! DelegationPolicy::permits($audience, $action)) {
                throw new IdentityDenied('delegation_forbidden', 403);
            }
            $membership = $this->authority->handle($actor, $tenant, $action, $scope);
            $sessionHash = hash('sha256', $session);
            $expires = Carbon::parse(DB::table('app.federated_sessions')->where('token_hash', $sessionHash)->value('expires_at'))->min(now()->addSeconds(60));
            if (DB::table('app.actor_delegations')->where('session_hash', $sessionHash)->whereNull('revoked_at')->where('expires_at', '>', now())->count() >= 1000) {
                throw new IdentityDenied('delegation_limit', 429);
            }
            $token = bin2hex(random_bytes(32));
            $id = (string) Str::uuid();
            DB::table('app.actor_delegations')->insert([
                'id' => $id, 'token_hash' => hash('sha256', $token), 'session_hash' => $sessionHash,
                'tenant_id' => $tenant, 'actor_id' => $actor->subject, 'audience' => $audience, 'action' => $action,
                'scope_json' => json_encode($scope, JSON_THROW_ON_ERROR), 'authority_fingerprint' => AuthorizeTenant::fingerprint($membership),
                'service_fingerprint' => $this->credentials->fingerprint($audience), 'console_fingerprint' => $this->credentials->fingerprint('console'),
                'created_at' => now(), 'expires_at' => $expires,
            ]);
            DB::table('app.delegation_audit')->insert(['id' => (string) Str::uuid(), 'delegation_id' => $id,
                'tenant_id' => $tenant, 'actor_id' => $actor->subject, 'event' => 'issued', 'occurred_at' => now()]);
            IdentityLedger::record('identity.delegation.issued', $actor->subject);

            return ['delegation_id' => $id, 'delegation_token' => $token, 'audience' => $audience,
                'expires_at' => $expires->toIso8601String(), 'authority_use' => 'request_bound'];
        });
    }
}
