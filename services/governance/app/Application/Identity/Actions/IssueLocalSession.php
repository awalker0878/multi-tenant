<?php

declare(strict_types=1);

namespace App\Application\Identity\Actions;

use App\Application\Identity\Data\LocalIdentity;
use App\Application\Identity\Data\SessionCredentials;
use App\Domain\Identity\BootstrapAdministrator;
use App\Domain\Identity\IdentityDenied;
use Illuminate\Support\Facades\DB;

final class IssueLocalSession
{
    // Internal action; callers hold the administrator lock in their transaction.
    public function handle(BootstrapAdministrator $administrator): SessionCredentials
    {
        if (! $administrator->allowsLocalLogin()) {
            throw new IdentityDenied('invalid_session');
        }
        $token = bin2hex(random_bytes(32));
        $changeRequired = $administrator->state === 'password_change_required';
        $expires = now()->addMinutes((int) config($changeRequired ? 'identity.change_session_minutes' : 'identity.session_minutes'));
        DB::table('app.identity_sessions')->insert([
            'token_hash' => hash('sha256', $token), 'audience' => 'console',
            'credential_version' => $administrator->credential_version,
            'created_at' => now(), 'expires_at' => $expires,
        ]);

        return new SessionCredentials($token, new LocalIdentity($changeRequired), $expires->toIso8601String());
    }
}
