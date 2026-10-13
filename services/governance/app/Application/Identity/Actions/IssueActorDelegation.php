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
    public function handle(#[\SensitiveParameter] string $session, string $tenant, string $audience, string $action, array $scope, string $key): array
    {
        return DB::transaction(function () use ($session, $tenant, $audience, $action, $scope, $key): array {
            BootstrapAdministrator::query()->lockForUpdate()->findOrFail(1);
            $actor = $this->authority->actor($session);
            if (! DelegationPolicy::permits($audience, $action)) {
                throw new IdentityDenied('delegation_forbidden', 403);
            }
            $membership = $this->authority->handle($actor, $tenant, $action, $scope);
            $sessionHash = hash('sha256', $session);
            if (! preg_match('/\\A[0-9a-f]{32,64}\\z/', $key)) {
                throw new IdentityDenied('idempotency_key_invalid', 422);
            }
            // Global bootstrap custody row is locked above. Under this same
            // transaction it serializes issuance across replicas, including
            // the absence of a prior key. Never persist or replay a raw token.
            DB::table('app.delegation_command_keys')->where('expires_at', '<=', now())->delete();
            $keyHash = hash('sha256', $key);
            if (DB::table('app.delegation_command_keys')
                ->where('session_hash', $sessionHash)->where('key_hash', $keyHash)->exists()) {
                throw new IdentityDenied('idempotency_key_conflict', 409);
            }
            $requestSha = hash('sha256', json_encode([
                'tenant_id' => $tenant, 'actor_id' => $actor->subject,
                'audience' => $audience, 'action' => $action, 'scope' => $scope,
            ], JSON_THROW_ON_ERROR | JSON_UNESCAPED_SLASHES));
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
            DB::table('app.delegation_command_keys')->insert([
                'session_hash' => $sessionHash, 'key_hash' => $keyHash,
                'request_sha256' => $requestSha, 'grant_id' => $id,
                'expires_at' => now()->addSeconds(300),
            ]);

            return ['delegation_id' => $id, 'delegation_token' => $token, 'audience' => $audience,
                'expires_at' => $expires->toIso8601String(), 'authority_use' => 'request_bound'];
        });
    }
}
