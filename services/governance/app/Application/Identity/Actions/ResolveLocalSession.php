<?php

declare(strict_types=1);

namespace App\Application\Identity\Actions;

use App\Application\Identity\Data\LocalIdentity;
use App\Domain\Identity\IdentityDenied;
use Illuminate\Support\Facades\DB;

final class ResolveLocalSession
{
    public function handle(#[\SensitiveParameter] string $token, bool $requireSetup = false): LocalIdentity
    {
        if (! preg_match('/\A[0-9a-f]{64}\z/', $token)) {
            throw new IdentityDenied('invalid_session');
        }
        // Join current identity state in one authoritative read. No cached privileges.
        $session = DB::table('app.identity_sessions as sessions')
            ->join('app.bootstrap_administrator as administrator', 'administrator.credential_version', '=', 'sessions.credential_version')
            ->where('administrator.id', 1)->whereIn('administrator.state', ['password_change_required', 'local_setup'])
            ->where('sessions.token_hash', hash('sha256', $token))->where('sessions.audience', 'console')
            ->whereNull('sessions.revoked_at')->where('sessions.expires_at', '>', now())
            ->first(['administrator.state']);
        if ($session === null) {
            throw new IdentityDenied('invalid_session');
        }
        $identity = new LocalIdentity($session->state === 'password_change_required');
        if ($requireSetup && $identity->passwordChangeRequired) {
            throw new IdentityDenied('password_change_required', 403);
        }

        return $identity;
    }
}
