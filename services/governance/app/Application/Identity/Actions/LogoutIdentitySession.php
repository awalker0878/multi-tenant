<?php

declare(strict_types=1);

namespace App\Application\Identity\Actions;

use App\Domain\Identity\BootstrapAdministrator;
use App\Domain\Identity\IdentityLedger;
use Illuminate\Support\Facades\DB;

final class LogoutIdentitySession
{
    public function handle(#[\SensitiveParameter] string $token, string $key, #[\SensitiveParameter] string $workload): void
    {
        DB::transaction(function () use ($token, $key, $workload): void {
            BootstrapAdministrator::query()->lockForUpdate()->findOrFail(1);
            $actor = DB::table('app.federated_sessions')->where('token_hash', hash('sha256', $token))->value('actor_id');
            $local = DB::table('app.identity_sessions')->where('token_hash', hash('sha256', $token))->exists();
            if (! is_string($actor) && ! $local) {
                return;
            }
            if (! IdentityLedger::command(is_string($actor) ? $actor : 'bootstrap-admin', 'logoutIdentitySession', $key, $workload, [], hash('sha256', $token), true)) {
                return;
            }
            $changed = DB::table('app.identity_sessions')->where('token_hash', hash('sha256', $token))
                ->where('audience', 'console')->whereNull('revoked_at')->update(['revoked_at' => now()]);
            $changed += DB::table('app.federated_sessions')->where('token_hash', hash('sha256', $token))
                ->where('audience', 'console')->whereNull('revoked_at')->update(['revoked_at' => now()]);
            if ($changed > 0) {
                IdentityLedger::record('identity.session.revoked', is_string($actor) ? $actor : 'bootstrap-admin');
            }
        });
    }
}
