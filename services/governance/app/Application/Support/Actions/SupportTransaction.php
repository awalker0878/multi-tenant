<?php

declare(strict_types=1);

namespace App\Application\Support\Actions;

use App\Application\Identity\Contracts\ConsoleCredential;
use App\Application\Identity\Data\FederatedIdentity;
use App\Application\Support\Contracts\SupportTrust;
use App\Application\Tenancy\Actions\AuthorizeTenant;
use App\Domain\Identity\BootstrapAdministrator;
use App\Domain\Identity\IdentityDenied;
use App\Domain\Support\SupportExpiry;
use App\Domain\Support\SupportLedger;
use App\Domain\Support\SupportTrustState;
use App\Domain\Tenancy\GovernanceLedger;
use Closure;
use Illuminate\Support\Facades\DB;
use stdClass;

final class SupportTransaction
{
    public function __construct(private readonly AuthorizeTenant $identity, private readonly SupportAuthority $authority, private readonly SupportTrust $trust, private readonly ConsoleCredential $credential) {}

    /** @param Closure(FederatedIdentity, ?SupportTrustState): (array<string, mixed>|IdentityDenied) $execute
     * @return array<string, mixed>
     */
    public function handle(#[\SensitiveParameter] string $token, #[\SensitiveParameter] string $workload, bool $online, Closure $execute, ?string $tenant = null, ?string $id = null): array
    {
        if (DB::transactionLevel() !== 0) {
            throw new IdentityDenied('support_transaction_unavailable', 503);
        }
        // Remote I/O must never hold the shared installation/tenant locks.
        $this->workload($workload);
        $this->identity->actor($token);
        try {
            $trust = $online ? $this->trust->current() : null;
        } catch (IdentityDenied $error) {
            if ($tenant !== null && $id !== null) {
                DB::transaction(function () use ($token, $workload, $tenant, $id): void {
                    BootstrapAdministrator::query()->lockForUpdate()->findOrFail(1);
                    $this->workload($workload);
                    $actor = $this->identity->actor($token);
                    $row = $this->request($actor, $tenant, $id);
                    $this->denial($row, $actor, 'trust_check', 'support_trust_unavailable');
                });
            }
            throw $error;
        }
        $result = DB::transaction(function () use ($token, $workload, $trust, $execute, $id): array|IdentityDenied {
            BootstrapAdministrator::query()->lockForUpdate()->findOrFail(1);
            $this->workload($workload);
            $actor = $this->identity->actor($token);
            if ($trust !== null) {
                if ($trust->observedAt < now()->subSeconds(5)->getTimestamp()
                    || $trust->connectionRevision !== DB::table('app.oidc_installation')->where('id', 1)->value('active_revision')) {
                    throw new IdentityDenied('support_trust_unavailable', 503);
                }
                if ($id === null) {
                    $this->authority->session(hash('sha256', $token), $actor->subject, $trust);
                }
            }

            return $execute($actor, $trust);
        });
        if ($result instanceof IdentityDenied) {
            throw $result;
        }

        return $result;
    }

    private function workload(#[\SensitiveParameter] string $token): void
    {
        if (! $this->credential->accepts($token)) {
            throw new IdentityDenied('invalid_workload_identity');
        }
    }

    /** @param array<string, mixed> $input
     * @param  Closure(): array<string, mixed>  $execute
     * @return array<string, mixed>
     */
    public function receipt(string $tenant, string $actor, string $command, string $key, array $input, Closure $execute): array
    {
        if (! preg_match('/\A[A-Za-z0-9_-]{8,128}\z/', $key)) {
            throw new IdentityDenied('invalid_idempotency_key', 422);
        }
        $digest = GovernanceLedger::digest($input);
        $receipt = DB::table('app.governance_commands')->where('scope_id', $tenant)->where('actor_id', $actor)
            ->where('command', $command)->where('request_key', $key)->first();
        if ($receipt !== null) {
            if (! hash_equals($receipt->digest, $digest)) {
                throw new IdentityDenied('idempotency_conflict', 409);
            }

            return json_decode($receipt->result_json, true, 32, JSON_THROW_ON_ERROR);
        }
        $result = $execute();
        DB::table('app.governance_commands')->insert(['scope_id' => $tenant, 'actor_id' => $actor, 'command' => $command,
            'request_key' => $key, 'digest' => $digest, 'result_json' => json_encode($result, JSON_THROW_ON_ERROR), 'created_at' => now()]);

        return $result;
    }

    public function request(FederatedIdentity $actor, string $tenant, string $id): stdClass
    {
        DB::table('app.tenants')->where('id', $tenant)->lockForUpdate()->first();
        $row = DB::table('app.support_requests')->where('tenant_id', $tenant)->where('id', $id)->lockForUpdate()->first();
        if ($row === null) {
            throw new IdentityDenied('not_found', 404);
        }
        $this->authority->visible($actor, $row, json_decode($row->binding_json, true, 32, JSON_THROW_ON_ERROR));
        SupportExpiry::apply($row);

        return $row;
    }

    /** @param Closure(): array<string, mixed> $execute
     * @return array<string, mixed>|IdentityDenied
     */
    public function audited(stdClass $row, FederatedIdentity $actor, string $operation, Closure $execute): array|IdentityDenied
    {
        try {
            return $execute();
        } catch (IdentityDenied $error) {
            $recorded = $this->denial($row, $actor, $operation, $error->reason);

            // Return the error through the transaction so denial/expiry facts commit.
            return $recorded ? $error : new IdentityDenied('support_denial_limit', 429);
        }
    }

    private function denial(stdClass $row, FederatedIdentity $actor, string $operation, string $reason): bool
    {
        if (DB::table('app.support_audit')->where('actor_id', $actor->subject)->where('event', 'support.access.denied')
            ->where('occurred_at', '>', now()->subMinute())->count() >= 60) {
            // Keep expiry/invalidation durable even when an actor exhausts the audit budget.
            return false;
        }
        SupportLedger::record($row->tenant_id, $actor->subject, 'support.access.denied', $row->id, $row->revision,
            ['binding_sha256' => $row->binding_sha256, 'operation' => $operation, 'reason_code' => $reason]);

        return true;
    }
}
