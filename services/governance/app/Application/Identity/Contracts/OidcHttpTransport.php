<?php

declare(strict_types=1);

namespace App\Application\Identity\Contracts;

use App\Domain\Identity\OidcConnection;

interface OidcHttpTransport
{
    /** @param array<string, string> $form
     * @return array<string, mixed>
     */
    public function request(OidcConnection $connection, string $url, #[\SensitiveParameter] array $form = []): array;
}
