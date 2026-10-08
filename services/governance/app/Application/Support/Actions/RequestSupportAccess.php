<?php

declare(strict_types=1);

namespace App\Application\Support\Actions;

use App\Application\Identity\Contracts\ServiceCredentials;
use App\Application\Identity\Data\FederatedIdentity;
use App\Application\Tenancy\Actions\AuthorizeTenant;
use App\Domain\Identity\IdentityDenied;
use App\Domain\Support\SupportLedger;
use App\Domain\Support\SupportPolicy;
use App\Domain\Support\SupportTrustState;
use App\Domain\Tenancy\GovernanceLedger;
use Illuminate\Support\Carbon;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Str;

final class RequestSupportAccess
{
    public function __construct(private readonly SupportTransaction $transaction, private readonly SupportAuthority $authority, private readonly ServiceCredentials $credentials) {}

    /** @param array<string, mixed> $input
     * @return array<string, mixed>
     */
    public function handle(#[\SensitiveParameter] string $token, #[\SensitiveParameter] string $workload, string $tenant, string $key, array $input): array
    {
        return $this->transaction->handle($token, $workload, true, function (FederatedIdentity $actor, ?SupportTrustState $trust) use ($token, $tenant, $key, $input): array {
            if ($trust === null) {
                throw new IdentityDenied('support_trust_unavailable', 503);
            }
            DB::table('app.tenants')->where('id', $tenant)->lockForUpdate()->first();
            $member = $this->authority->membership($actor->subject, $tenant, $input);
            $session = $this->authority->session(hash('sha256', $token), $actor->subject, $trust, true);

            return $this->transaction->receipt($tenant, $actor->subject, 'support.request', $key, $input, function () use ($actor, $tenant, $input, $member, $session, $token, $trust): array {
                $expires = Carbon::parse($input['expires_at']);
                if ($expires->lte(now()) || $expires->gt(now()->addMinutes(SupportPolicy::MAX_MINUTES))) {
                    throw new IdentityDenied('invalid_support_expiry', 422);
                }
                $executor = DB::table('app.federated_actors as a')->join('app.oidc_connections as c', 'c.issuer', '=', 'a.issuer')
                    ->where('c.revision', $trust->connectionRevision)->where('a.id', $input['executor_id'])->whereNull('a.disabled_at')->exists();
                if (! $executor) {
                    throw new IdentityDenied('support_binding_invalid', 422);
                }
                if (DB::table('app.support_requests')->where('requester_id', $actor->subject)
                    ->where('created_at', '>', now()->subHour())->count() >= 20) {
                    throw new IdentityDenied('support_request_limit', 429);
                }
                $resources = $input['resources'];
                usort($resources, static fn (array $a, array $b): int => [$a['kind'], $a['id']] <=> [$b['kind'], $b['id']]);
                if (count(array_unique(array_column($resources, 'id'))) !== count($resources)) {
                    throw new IdentityDenied('support_binding_invalid', 422);
                }
                $actions = $input['actions'];
                sort($actions, SORT_STRING);
                foreach ($resources as $resource) {
                    if (! in_array($resource['kind'], array_map(static fn (string $action): string => SupportPolicy::ACTIONS[$action], $actions), true)) {
                        throw new IdentityDenied('support_binding_invalid', 422);
                    }
                }
                $expires = $expires->min(Carbon::parse($session->expires_at));
                if ($member->expires_at !== null) {
                    $expires = $expires->min(Carbon::parse($member->expires_at));
                }
                $id = (string) Str::uuid();
                $binding = ['policy_version' => SupportPolicy::VERSION, 'tenant_id' => $tenant,
                    'tenant_revision' => DB::table('app.tenants')->where('id', $tenant)->value('revision'),
                    'requester_id' => $actor->subject, 'executor_id' => $input['executor_id'],
                    'site_id' => $input['site_id'], 'environment' => $input['environment'],
                    'resources' => $resources, 'actions' => $actions, 'reason_code' => $input['reason_code'],
                    'case_reference' => $input['case_reference'], 'expires_at' => $expires->utc()->toIso8601String(),
                    'installation_binding' => (string) DB::table('app.identity_admission')->where('id', 1)->value('binding_sha256')];
                $digest = GovernanceLedger::digest($binding);
                DB::table('app.support_requests')->insert(['id' => $id, 'tenant_id' => $tenant,
                    'requester_id' => $actor->subject, 'executor_id' => $input['executor_id'],
                    'binding_json' => json_encode($binding, JSON_THROW_ON_ERROR), 'binding_sha256' => $digest,
                    'policy_version' => SupportPolicy::VERSION, 'requester_authority' => AuthorizeTenant::fingerprint($member),
                    'requester_session_hash' => hash('sha256', $token), 'admission_binding' => $binding['installation_binding'],
                    'console_fingerprint' => $this->credentials->fingerprint('console'), 'connection_revision' => $trust->connectionRevision,
                    'state' => 'requested', 'revision' => 1, 'expires_at' => $expires, 'created_at' => now()]);
                SupportLedger::record($tenant, $actor->subject, 'support.access.requested', $id, 1, ['binding_sha256' => $digest, 'binding' => $binding]);

                return ['id' => $id, 'state' => 'requested', 'revision' => 1, 'binding_sha256' => $digest,
                    'binding' => $binding, 'authority_use' => 'request_status_only'];
            });
        });
    }
}
