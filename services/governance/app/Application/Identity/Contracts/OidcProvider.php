<?php

declare(strict_types=1);

namespace App\Application\Identity\Contracts;

use App\Domain\Identity\OidcConnection;

interface OidcProvider
{
    /** @return array{authorization_endpoint: string, token_endpoint: string, jwks_uri: string} */
    public function discover(OidcConnection $connection): array;

    /** @param array{verifier: string, nonce: string, endpoints: array{authorization_endpoint: string, token_endpoint: string, jwks_uri: string}} $context
     * @return array{subject: string, expires_at: int, key_thumbprint: string}
     */
    public function authenticate(OidcConnection $connection, #[\SensitiveParameter] string $code, #[\SensitiveParameter] array $context): array;
}
