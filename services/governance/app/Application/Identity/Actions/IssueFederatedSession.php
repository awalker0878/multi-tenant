<?php

declare(strict_types=1);

namespace App\Application\Identity\Actions;

use App\Application\Identity\Data\FederatedIdentity;
use App\Application\Identity\Data\SessionCredentials;
use Illuminate\Support\Facades\DB;

final class IssueFederatedSession
{
    // The caller holds the installation lock and has checked the active revision.
    public function handle(string $actorId, int $revision, int $expiresAt, bool $administrator): SessionCredentials
    {
        $token = bin2hex(random_bytes(32));
        $expires = now()->addMinutes(30)->min(now()->setTimestamp($expiresAt));
        DB::table('app.federated_sessions')->insert([
            'token_hash' => hash('sha256', $token), 'actor_id' => $actorId, 'connection_revision' => $revision,
            'audience' => 'console', 'created_at' => now(), 'expires_at' => $expires,
        ]);

        return new SessionCredentials($token, new FederatedIdentity($actorId, $administrator), $expires->toIso8601String());
    }
}
