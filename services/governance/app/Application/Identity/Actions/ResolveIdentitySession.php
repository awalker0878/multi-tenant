<?php

declare(strict_types=1);

namespace App\Application\Identity\Actions;

use App\Application\Identity\Data\FederatedIdentity;
use App\Application\Identity\Data\LocalIdentity;
use App\Domain\Identity\IdentityDenied;
use Illuminate\Support\Facades\DB;

final class ResolveIdentitySession
{
    public function __construct(private readonly ResolveLocalSession $local, private readonly CheckIdentityAdmission $admission) {}

    public function handle(#[\SensitiveParameter] string $token, bool $requireSetup = false): LocalIdentity|FederatedIdentity
    {
        $this->admission->handle();
        if (! preg_match('/\A[0-9a-f]{64}\z/', $token)) {
            throw new IdentityDenied('invalid_session');
        }
        $session = DB::table('app.federated_sessions as sessions')
            ->join('app.federated_actors as actors', 'actors.id', '=', 'sessions.actor_id')
            ->join('app.oidc_installation as installation', 'installation.active_revision', '=', 'sessions.connection_revision')
            ->join('app.oidc_connections as connection', 'connection.revision', '=', 'installation.active_revision')
            ->where('installation.id', 1)->where('sessions.token_hash', hash('sha256', $token))
            ->where('sessions.audience', 'console')->whereNull('sessions.revoked_at')->whereNull('actors.disabled_at')
            ->where('sessions.expires_at', '>', now())->whereColumn('actors.issuer', 'connection.issuer')
            ->first(['actors.id', 'actors.subject', 'connection.administrator_subject']);
        if ($session === null) {
            return $this->local->handle($token, $requireSetup);
        }
        $actor = new FederatedIdentity($session->id, $session->subject === $session->administrator_subject);
        if ($requireSetup && ! $actor->installationAdministrator) {
            throw new IdentityDenied('forbidden', 403);
        }

        return $actor;
    }
}
