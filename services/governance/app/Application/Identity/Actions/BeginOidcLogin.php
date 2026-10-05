<?php

declare(strict_types=1);

namespace App\Application\Identity\Actions;

use App\Application\Identity\Contracts\OidcProvider;
use App\Domain\Identity\BootstrapAdministrator;
use App\Domain\Identity\IdentityDenied;
use App\Domain\Identity\OidcConnection;
use Illuminate\Support\Facades\Crypt;
use Illuminate\Support\Facades\DB;

final class BeginOidcLogin
{
    public function __construct(private readonly ResolveIdentitySession $resolve, private readonly OidcProvider $provider) {}

    /** @return array{authorization_url: string} */
    public function handle(string $purpose, #[\SensitiveParameter] string $browser, #[\SensitiveParameter] string $token = ''): array
    {
        $connection = DB::transaction(function () use ($purpose, $token): OidcConnection {
            BootstrapAdministrator::query()->lockForUpdate()->findOrFail(1);
            if ($purpose === 'setup') {
                $this->resolve->handle($token, requireSetup: true);
            }
            $installation = DB::table('app.oidc_installation')->where('id', 1)->first();
            $revision = $purpose === 'setup' ? $installation?->latest_revision : $installation?->active_revision;
            $connection = OidcConnection::query()->where('revision', $revision)->first();
            if ($connection === null) {
                throw new IdentityDenied('oidc_unavailable', 409);
            }

            return $connection;
        });
        $endpoints = $this->provider->discover($connection);
        $state = bin2hex(random_bytes(32));
        $nonce = bin2hex(random_bytes(32));
        $verifier = bin2hex(random_bytes(32));
        DB::table('app.oidc_flows')->insert([
            'state_hash' => hash('sha256', $state), 'browser_hash' => hash('sha256', $browser),
            'initiator_hash' => $purpose === 'setup' ? hash('sha256', $token) : null,
            'purpose' => $purpose, 'connection_revision' => $connection->revision,
            'protected_context' => Crypt::encryptString(json_encode(compact('verifier', 'nonce', 'endpoints'), JSON_THROW_ON_ERROR)),
            'expires_at' => now()->addMinutes(5),
        ]);
        $query = http_build_query([
            'response_type' => 'code', 'client_id' => $connection->client_id,
            'redirect_uri' => $connection->redirect_uri, 'scope' => 'openid',
            'state' => $state, 'nonce' => $nonce, 'code_challenge_method' => 'S256',
            'code_challenge' => rtrim(strtr(base64_encode(hash('sha256', $verifier, true)), '+/', '-_'), '='),
            'prompt' => 'login', 'max_age' => '0',
        ], '', '&', PHP_QUERY_RFC3986);

        return ['authorization_url' => $endpoints['authorization_endpoint'].'?'.$query];
    }
}
