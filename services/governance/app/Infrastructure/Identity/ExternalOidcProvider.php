<?php

declare(strict_types=1);

namespace App\Infrastructure\Identity;

use App\Application\Identity\Contracts\OidcHttpTransport;
use App\Application\Identity\Contracts\OidcProvider;
use App\Domain\Identity\IdentityDenied;
use App\Domain\Identity\OidcConnection;
use App\Domain\Identity\OidcUrl;
use Firebase\JWT\JWK;
use Firebase\JWT\JWT;
use Illuminate\Support\Facades\Crypt;
use Illuminate\Support\Facades\DB;
use stdClass;
use Throwable;

final class ExternalOidcProvider implements OidcProvider
{
    public function __construct(private readonly OidcHttpTransport $http) {}

    public function discover(OidcConnection $connection): array
    {
        $metadata = $this->http->request($connection, rtrim($connection->issuer, '/').'/.well-known/openid-configuration');
        if (($metadata['issuer'] ?? null) !== $connection->issuer
            || ! in_array('code', (array) ($metadata['response_types_supported'] ?? []), true)
            || ! in_array('S256', (array) ($metadata['code_challenge_methods_supported'] ?? []), true)
            || ! in_array('RS256', (array) ($metadata['id_token_signing_alg_values_supported'] ?? []), true)
            || ! in_array('client_secret_post', (array) ($metadata['token_endpoint_auth_methods_supported'] ?? []), true)) {
            throw new IdentityDenied('unsupported_provider', 422);
        }
        $endpoints = [];
        foreach (['authorization_endpoint', 'token_endpoint', 'jwks_uri'] as $name) {
            $url = $metadata[$name] ?? null;
            if (! is_string($url) || OidcUrl::origin($url) !== OidcUrl::origin($connection->issuer)) {
                throw new IdentityDenied('provider_endpoint_denied', 422);
            }
            $endpoints[$name] = $url;
        }

        return $endpoints;
    }

    public function authenticate(OidcConnection $connection, #[\SensitiveParameter] string $code, #[\SensitiveParameter] array $context): array
    {
        try {
            $ciphertext = DB::table('app.identity_secrets')->where('id', $connection->secret_ref)->value('ciphertext');
            if (! is_string($ciphertext)) {
                throw new IdentityDenied('secret_unavailable', 503);
            }
            $response = $this->http->request($connection, $context['endpoints']['token_endpoint'], [
                'grant_type' => 'authorization_code', 'code' => $code,
                'redirect_uri' => $connection->redirect_uri, 'client_id' => $connection->client_id,
                'client_secret' => Crypt::decryptString($ciphertext), 'code_verifier' => $context['verifier'],
            ]);
            $jwt = $response['id_token'] ?? null;
            if (! is_string($jwt) || strlen($jwt) > 32768) {
                throw new IdentityDenied('invalid_id_token');
            }
            $jwks = $this->http->request($connection, $context['endpoints']['jwks_uri']);
            $keys = $this->signingKeys($jwks);
            $headers = new stdClass;
            $claims = (array) JWT::decode($jwt, JWK::parseKeySet(['keys' => $keys], 'RS256'), $headers);
            if ($headers === null || $headers->alg !== 'RS256' || isset($headers->crit) || isset($headers->jku) || isset($headers->x5u)
                || ($claims['iss'] ?? null) !== $connection->issuer || ($claims['nonce'] ?? null) !== $context['nonce']) {
                throw new IdentityDenied('invalid_id_token');
            }
            $audience = $claims['aud'] ?? null;
            $audiences = is_string($audience) ? [$audience] : $audience;
            if (! is_array($audiences) || ! array_is_list($audiences) || ! in_array($connection->client_id, $audiences, true)
                || (count($audiences) > 1 && ($claims['azp'] ?? null) !== $connection->client_id)
                || (isset($claims['azp']) && $claims['azp'] !== $connection->client_id)) {
                throw new IdentityDenied('invalid_id_token');
            }
            $now = now()->getTimestamp();
            foreach (['iat', 'exp', 'auth_time'] as $time) {
                if (! is_int($claims[$time] ?? null)) {
                    throw new IdentityDenied('invalid_id_token');
                }
            }
            $subject = $claims['sub'] ?? null;
            if (! is_string($subject) || $subject === '' || strlen($subject) > 255 || preg_match('/[\x00-\x1f\x7f]/', $subject)
                || $claims['exp'] <= $now || $claims['iat'] > $now + 30 || $claims['iat'] < $now - 300
                || $claims['auth_time'] > $now + 30 || $claims['auth_time'] < $now - 300
                || (isset($claims['nbf']) && (! is_int($claims['nbf']) || $claims['nbf'] > $now + 30))) {
                throw new IdentityDenied('invalid_id_token');
            }

            return ['subject' => $subject, 'expires_at' => $claims['exp']];
        } catch (IdentityDenied $error) {
            throw $error;
        } catch (Throwable) {
            // Library/network/secret errors may contain token bytes. Do not chain them.
            throw new IdentityDenied('invalid_id_token');
        }
    }

    /** @param array<string, mixed> $jwks
     * @return list<array<string, mixed>>
     */
    private function signingKeys(array $jwks): array
    {
        $keys = $jwks['keys'] ?? null;
        if (! is_array($keys) || ! array_is_list($keys) || count($keys) > 50) {
            throw new IdentityDenied('invalid_provider_keys');
        }
        $valid = [];
        $seen = [];
        foreach ($keys as $key) {
            if (! is_array($key) || ($key['kty'] ?? null) !== 'RSA' || ($key['alg'] ?? 'RS256') !== 'RS256'
                || ($key['use'] ?? 'sig') !== 'sig' || (isset($key['key_ops']) && $key['key_ops'] !== ['verify'])) {
                continue;
            }
            $kid = $key['kid'] ?? null;
            if (! is_string($kid) || $kid === '' || isset($seen[$kid]) || ! is_string($key['n'] ?? null)
                || strlen(JWT::urlsafeB64Decode($key['n'])) < 256 || isset($key['d'])) {
                throw new IdentityDenied('invalid_provider_keys');
            }
            $seen[$kid] = true;
            $valid[] = $key;
        }
        if ($valid === []) {
            throw new IdentityDenied('invalid_provider_keys');
        }

        return $valid;
    }
}
