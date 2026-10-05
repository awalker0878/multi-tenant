<?php

declare(strict_types=1);

namespace App\Application\Identity\Actions;

use App\Application\Identity\Contracts\OidcProvider;
use App\Application\Identity\Data\SessionCredentials;
use App\Domain\Identity\BootstrapAdministrator;
use App\Domain\Identity\IdentityDenied;
use App\Domain\Identity\IdentityLedger;
use App\Domain\Identity\OidcConnection;
use Illuminate\Support\Carbon;
use Illuminate\Support\Facades\Crypt;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Str;

final class CompleteOidcLogin
{
    public function __construct(private readonly ResolveIdentitySession $resolve, private readonly OidcProvider $provider, private readonly IssueFederatedSession $sessions, private readonly CheckIdentityAdmission $admission) {}

    /** @return SessionCredentials|array{verification_token: string, revision: int, subject: string} */
    public function handle(#[\SensitiveParameter] string $state, #[\SensitiveParameter] string $browser, #[\SensitiveParameter] string $code, #[\SensitiveParameter] string $token = ''): SessionCredentials|array
    {
        $this->admission->handle();
        // Consume before remote I/O. An interrupted or failed exchange cannot be replayed.
        $flow = DB::transaction(function () use ($state, $browser, $token): \stdClass {
            BootstrapAdministrator::query()->lockForUpdate()->findOrFail(1);
            $flow = DB::table('app.oidc_flows')->where('state_hash', hash('sha256', $state))->lockForUpdate()->first();
            if ($flow === null || $flow->consumed_at !== null || Carbon::parse($flow->expires_at)->isPast()
                || ! hash_equals($flow->browser_hash, hash('sha256', $browser))) {
                throw new IdentityDenied('invalid_oidc_flow');
            }
            $this->admission->handle();
            $this->checkCurrent($flow, $token);
            DB::table('app.oidc_flows')->where('state_hash', $flow->state_hash)->update(['consumed_at' => now()]);

            return $flow;
        });
        $connection = OidcConnection::query()->where('revision', $flow->connection_revision)->firstOrFail();
        $context = json_decode(Crypt::decryptString($flow->protected_context), true, 16, JSON_THROW_ON_ERROR);
        $verified = $this->provider->authenticate($connection, $code, $context);

        return DB::transaction(function () use ($flow, $connection, $verified, $token): SessionCredentials|array {
            BootstrapAdministrator::query()->lockForUpdate()->findOrFail(1);
            DB::table('app.oidc_installation')->where('id', 1)->lockForUpdate()->first();
            $this->admission->handle();
            $this->checkCurrent($flow, $token);
            if ($verified['expires_at'] <= now()->getTimestamp() || ($flow->purpose === 'setup' && $verified['subject'] !== $connection->administrator_subject)) {
                throw new IdentityDenied('administrator_not_verified', 403);
            }
            $actor = DB::table('app.federated_actors')->where('issuer', $connection->issuer)->where('subject', $verified['subject'])->first();
            if ($actor?->disabled_at !== null) {
                throw new IdentityDenied('forbidden', 403);
            }
            $id = $actor->id ?? (string) Str::uuid();
            if ($actor === null) {
                DB::table('app.federated_actors')->insert(['id' => $id, 'issuer' => $connection->issuer, 'subject' => $verified['subject']]);
            }
            if ($flow->purpose === 'login') {
                IdentityLedger::record('identity.federated.login', $id);

                return $this->sessions->handle($id, $connection->revision, $verified['expires_at'], $verified['subject'] === $connection->administrator_subject, $verified['key_thumbprint']);
            }
            $proof = bin2hex(random_bytes(32));
            DB::table('app.oidc_verifications')->insert([
                'proof_hash' => hash('sha256', $proof), 'initiator_hash' => $flow->initiator_hash,
                'actor_id' => $id, 'connection_revision' => $connection->revision,
                'provider_key_sha256' => $verified['key_thumbprint'],
                'expires_at' => now()->addMinutes(5)->min(now()->setTimestamp($verified['expires_at'])),
            ]);
            IdentityLedger::record('identity.oidc.administrator_verified', $id);

            return ['verification_token' => $proof, 'revision' => $connection->revision, 'subject' => $id];
        });
    }

    private function checkCurrent(\stdClass $flow, #[\SensitiveParameter] string $token): void
    {
        $installation = DB::table('app.oidc_installation')->where('id', 1)->first();
        $current = $flow->purpose === 'setup' ? $installation?->latest_revision : $installation?->active_revision;
        if ($flow->connection_revision !== $current || Carbon::parse($flow->expires_at)->isPast()) {
            throw new IdentityDenied('revision_conflict', 409);
        }
        if ($flow->purpose === 'setup') {
            $this->resolve->handle($token, requireSetup: true);
            if (! hash_equals($flow->initiator_hash, hash('sha256', $token))) {
                throw new IdentityDenied('invalid_oidc_flow');
            }
        }
    }
}
