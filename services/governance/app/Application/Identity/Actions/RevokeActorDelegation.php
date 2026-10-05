<?php

declare(strict_types=1);

namespace App\Application\Identity\Actions;

use App\Application\Tenancy\Actions\AuthorizeTenant;
use App\Domain\Identity\BootstrapAdministrator;
use App\Domain\Identity\IdentityDenied;
use App\Domain\Identity\IdentityLedger;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Str;

final class RevokeActorDelegation
{
    public function __construct(private readonly AuthorizeTenant $authority) {}

    public function handle(#[\SensitiveParameter] string $token, string $tenant, string $id): void
    {
        DB::transaction(function () use ($token, $tenant, $id): void {
            BootstrapAdministrator::query()->lockForUpdate()->findOrFail(1);
            $actor = $this->authority->actor($token);
            $grant = DB::table('app.actor_delegations')->where('id', $id)->where('tenant_id', $tenant)->where('actor_id', $actor->subject)->lockForUpdate()->first();
            // The originating actor can relinquish its own delegation even after
            // tenant membership was revoked. It cannot inspect or revoke another's.
            if ($grant === null) {
                throw new IdentityDenied('not_found', 404);
            }
            if ($grant->revoked_at === null) {
                DB::table('app.actor_delegations')->where('id', $id)->update(['revoked_at' => now()]);
                DB::table('app.delegation_audit')->insert(['id' => (string) Str::uuid(), 'delegation_id' => $id,
                    'tenant_id' => $tenant, 'actor_id' => $actor->subject, 'event' => 'revoked', 'occurred_at' => now()]);
                IdentityLedger::record('identity.delegation.revoked', $actor->subject);
            }
        });
    }
}
