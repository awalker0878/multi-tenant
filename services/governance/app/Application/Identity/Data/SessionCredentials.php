<?php

declare(strict_types=1);

namespace App\Application\Identity\Data;

final readonly class SessionCredentials
{
    public function __construct(
        #[\SensitiveParameter] public string $token,
        public LocalIdentity $identity,
        public string $expiresAt,
    ) {}
}
