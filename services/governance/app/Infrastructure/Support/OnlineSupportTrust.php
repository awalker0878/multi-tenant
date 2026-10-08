<?php

declare(strict_types=1);

namespace App\Infrastructure\Support;

use App\Application\Identity\Contracts\OidcHttpTransport;
use App\Application\Identity\Contracts\OidcProvider;
use App\Application\Support\Contracts\SupportTrust;
use App\Domain\Identity\IdentityDenied;
use App\Domain\Identity\OidcConnection;
use App\Domain\Support\SupportTrustState;
use App\Infrastructure\Identity\ExternalOidcProvider;
use Firebase\JWT\JWK;
use Illuminate\Support\Facades\Crypt;
use Illuminate\Support\Facades\DB;
use Throwable;

final class OnlineSupportTrust implements SupportTrust
{
    public function __construct(private readonly OidcProvider $provider, private readonly OidcHttpTransport $http) {}

    public function current(): SupportTrustState
    {
        try {
            $revision = DB::table('app.oidc_installation')->where('id', 1)->value('active_revision');
            $connection = OidcConnection::query()->where('revision', $revision)->first();
            if ($connection === null) {
                throw new IdentityDenied('support_trust_unavailable', 503);
            }
            // Exercise current encryption-key custody without returning or logging the secret.
            $cipher = DB::table('app.identity_secrets')->where('id', $connection->secret_ref)->value('ciphertext');
            if (! is_string($cipher) || Crypt::decryptString($cipher) === '') {
                throw new IdentityDenied('support_trust_unavailable', 503);
            }
            $endpoints = $this->provider->discover($connection);
            $keys = ExternalOidcProvider::signingKeys($this->http->request($connection, $endpoints['jwks_uri']));
            JWK::parseKeySet(['keys' => $keys], 'RS256');

            return new SupportTrustState($connection->revision, array_map(ExternalOidcProvider::thumbprint(...), $keys), now()->getTimestamp());
        } catch (Throwable) {
            throw new IdentityDenied('support_trust_unavailable', 503);
        }
    }
}
