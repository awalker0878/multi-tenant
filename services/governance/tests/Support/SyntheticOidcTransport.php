<?php

declare(strict_types=1);

namespace Tests\Support;

use App\Application\Identity\Contracts\OidcHttpTransport;
use App\Domain\Identity\IdentityDenied;
use App\Domain\Identity\OidcConnection;
use Firebase\JWT\JWT;

final class SyntheticOidcTransport implements OidcHttpTransport
{
    public array $codes = [];

    public array $claims = [];

    public array $metadata = [];

    public bool $unavailable = false;

    public bool $badSignature = false;

    public array $requests = [];

    private string $key;

    private array $jwk;

    public function __construct()
    {
        static $key = null;
        $key ??= openssl_pkey_new(['private_key_bits' => 2048, 'private_key_type' => OPENSSL_KEYTYPE_RSA]);
        openssl_pkey_export($key, $private);
        $this->key = $private;
        $details = openssl_pkey_get_details($key);
        $this->jwk = ['kty' => 'RSA', 'alg' => 'RS256', 'use' => 'sig', 'kid' => 'fixture',
            'n' => JWT::urlsafeB64Encode($details['rsa']['n']), 'e' => JWT::urlsafeB64Encode($details['rsa']['e'])];
    }

    public function authorize(string $url): array
    {
        parse_str(parse_url($url, PHP_URL_QUERY), $query);
        $code = bin2hex(random_bytes(24));
        $this->codes[$code] = $query;

        return ['state' => $query['state'], 'code' => $code];
    }

    public function request(OidcConnection $connection, string $url, #[\SensitiveParameter] array $form = []): array
    {
        $this->requests[] = $url;
        if ($this->unavailable) {
            throw new IdentityDenied('provider_unavailable', 503);
        }
        if (str_ends_with($url, '/.well-known/openid-configuration')) {
            return array_replace([
                'issuer' => $connection->issuer, 'authorization_endpoint' => $connection->issuer.'/authorize',
                'token_endpoint' => $connection->issuer.'/token', 'jwks_uri' => $connection->issuer.'/keys',
                'response_types_supported' => ['code'], 'code_challenge_methods_supported' => ['S256'],
                'id_token_signing_alg_values_supported' => ['RS256'], 'token_endpoint_auth_methods_supported' => ['client_secret_post'],
            ], $this->metadata);
        }
        if (str_ends_with($url, '/keys')) {
            return ['keys' => [$this->jwk]];
        }
        $request = $this->codes[$form['code']] ?? null;
        unset($this->codes[$form['code']]);
        if ($request === null || $form['client_id'] !== $request['client_id'] || $form['redirect_uri'] !== $request['redirect_uri']
            || JWT::urlsafeB64Encode(hash('sha256', $form['code_verifier'], true)) !== $request['code_challenge']
            || $form['client_secret'] !== 'synthetic-oidc-secret') {
            throw new IdentityDenied('invalid_code');
        }
        $claims = array_replace([
            'iss' => $connection->issuer, 'sub' => $connection->administrator_subject, 'aud' => $connection->client_id,
            'iat' => time(), 'exp' => time() + 3600, 'auth_time' => time(), 'nonce' => $request['nonce'],
        ], $this->claims);
        $token = JWT::encode($claims, $this->key, 'RS256', 'fixture');
        if ($this->badSignature) {
            $parts = explode('.', $token);
            $parts[2] = JWT::urlsafeB64Encode(random_bytes(256));
            $token = implode('.', $parts);
        }

        return ['id_token' => $token, 'access_token' => 'must-not-be-persisted'];
    }
}
