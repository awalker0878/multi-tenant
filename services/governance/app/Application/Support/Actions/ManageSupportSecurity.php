<?php

declare(strict_types=1);

namespace App\Application\Support\Actions;

use App\Application\Identity\Data\FederatedIdentity;
use App\Domain\Identity\IdentityDenied;
use App\Domain\Support\SupportLedger;
use App\Domain\Support\SupportTrustState;
use Illuminate\Support\Carbon;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Str;

final class ManageSupportSecurity
{
    public function __construct(private readonly SupportTransaction $transaction, private readonly SupportAuthority $authority) {}

    /** @param array<string, mixed> $input
     * @return array<string, mixed>
     */
    public function handle(#[\SensitiveParameter] string $token, #[\SensitiveParameter] string $workload, string $operation, string $key, array $input): array
    {
        return $this->transaction->handle($token, $workload, $operation === 'grant', function (FederatedIdentity $actor, ?SupportTrustState $trust) use ($token, $operation, $key, $input): array {
            if (! $actor->installationAdministrator) {
                throw new IdentityDenied('forbidden', 403);
            }
            if ($operation === 'grant') {
                if ($trust === null) {
                    throw new IdentityDenied('support_trust_unavailable', 503);
                }
                $this->authority->session(hash('sha256', $token), $actor->subject, $trust, true);
            }
            $tenant = $input['tenant_id'];
            if (! DB::table('app.tenants')->where('id', $tenant)->lockForUpdate()->exists()) {
                throw new IdentityDenied('not_found', 404);
            }

            return $this->transaction->receipt($tenant, $actor->subject, 'support.security.'.$operation, $key, $input, function () use ($actor, $operation, $input, $tenant, $trust): array {
                if ($operation === 'revoke') {
                    $grant = DB::table('app.support_security_grants')->where('tenant_id', $tenant)->where('id', $input['grant_id'])->lockForUpdate()->first();
                    if ($grant === null) {
                        throw new IdentityDenied('not_found', 404);
                    }
                    if ($grant->revision !== $input['revision'] || $grant->revoked_at !== null) {
                        throw new IdentityDenied('revision_conflict', 409);
                    }
                    DB::table('app.support_security_grants')->where('id', $grant->id)->update(['revoked_at' => now(), 'revision' => $grant->revision + 1]);
                    SupportLedger::record($tenant, $actor->subject, 'support.security.revoked', $grant->id, $grant->revision + 1,
                        ['case_reference' => $input['case_reference'], 'reason_code' => $input['reason_code']]);

                    return ['id' => $grant->id, 'revision' => $grant->revision + 1, 'state' => 'revoked'];
                }
                if ($trust === null || $input['actor_id'] === $actor->subject) {
                    throw new IdentityDenied('independent_assignment_required', 403);
                }
                $expires = Carbon::parse($input['expires_at']);
                if ($expires->lte(now()) || $expires->gt(now()->addDays(30))) {
                    throw new IdentityDenied('invalid_support_expiry', 422);
                }
                if (! DB::table('app.federated_actors as a')->join('app.oidc_connections as c', 'c.issuer', '=', 'a.issuer')
                    ->where('c.revision', $trust->connectionRevision)->where('a.id', $input['actor_id'])->whereNull('a.disabled_at')->exists()) {
                    throw new IdentityDenied('support_binding_invalid', 422);
                }
                if (DB::table('app.support_security_grants')->where('granted_by', $actor->subject)->where('created_at', '>', now()->subHour())->count() >= 100) {
                    throw new IdentityDenied('support_assignment_limit', 429);
                }
                $id = (string) Str::uuid();
                $grant = ['id' => $id, 'tenant_id' => $tenant, 'actor_id' => $input['actor_id'], 'role' => $input['role'],
                    'site_id' => $input['site_id'], 'environment' => $input['environment'], 'granted_by' => $actor->subject,
                    'expires_at' => $expires, 'created_at' => now(), 'revision' => 1];
                DB::table('app.support_security_grants')->insert($grant);
                SupportLedger::record($tenant, $actor->subject, 'support.security.granted', $id, 1,
                    ['actor_id' => $input['actor_id'], 'role' => $input['role'], 'site_id' => $input['site_id'],
                        'environment' => $input['environment'], 'expires_at' => $expires->toIso8601String(), 'case_reference' => $input['case_reference']]);

                return ['id' => $id, 'revision' => 1, 'actor_id' => $input['actor_id'], 'role' => $input['role'], 'expires_at' => $expires->toIso8601String()];
            });
        });
    }
}
