<?php

declare(strict_types=1);

namespace App\Application\Identity\Actions;

use App\Application\Identity\Data\SessionCredentials;
use App\Domain\Identity\BootstrapAdministrator;
use App\Domain\Identity\IdentityDenied;
use App\Domain\Identity\IdentityLedger;
use Illuminate\Support\Carbon;
use Illuminate\Support\Facades\DB;

final class ActivateOidcConnection
{
    public function __construct(private readonly ResolveIdentitySession $resolve, private readonly IssueFederatedSession $sessions) {}

    public function handle(#[\SensitiveParameter] string $token, #[\SensitiveParameter] string $proof): SessionCredentials
    {
        return DB::transaction(function () use ($token, $proof): SessionCredentials {
            $bootstrap = BootstrapAdministrator::query()->lockForUpdate()->findOrFail(1);
            $this->resolve->handle($token, requireSetup: true);
            $installation = DB::table('app.oidc_installation')->where('id', 1)->lockForUpdate()->first();
            $verified = DB::table('app.oidc_verifications')->where('proof_hash', hash('sha256', $proof))->lockForUpdate()->first();
            if ($verified === null || $verified->consumed_at !== null || Carbon::parse($verified->expires_at)->isPast()
                || $verified->connection_revision !== $installation?->latest_revision || ! hash_equals($verified->initiator_hash, hash('sha256', $token))) {
                throw new IdentityDenied('invalid_verification', 409);
            }
            if (! DB::table('app.federated_actors')->where('id', $verified->actor_id)->whereNull('disabled_at')->exists()) {
                throw new IdentityDenied('forbidden', 403);
            }
            DB::table('app.oidc_installation')->where('id', 1)->update(['active_revision' => $verified->connection_revision]);
            $bootstrap->forceFill(['state' => 'retired', 'password_hash' => null, 'retired_at' => $bootstrap->retired_at ?? now(), 'credential_version' => $bootstrap->credential_version + 1])->save();
            DB::table('app.identity_sessions')->whereNull('revoked_at')->update(['revoked_at' => now()]);
            DB::table('app.federated_sessions')->whereNull('revoked_at')->update(['revoked_at' => now()]);
            DB::table('app.oidc_verifications')->where('proof_hash', $verified->proof_hash)->update(['consumed_at' => now()]);
            IdentityLedger::record('identity.oidc.activated', $verified->actor_id);

            // The tested proof is short lived; handover requires a fresh provider sign-in thereafter.
            return $this->sessions->handle($verified->actor_id, $verified->connection_revision, Carbon::parse($verified->expires_at)->getTimestamp(), true);
        });
    }
}
