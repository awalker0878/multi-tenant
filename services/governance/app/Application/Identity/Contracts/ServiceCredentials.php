<?php

declare(strict_types=1);

namespace App\Application\Identity\Contracts;

interface ServiceCredentials
{
    public function authenticate(#[\SensitiveParameter] string $token): string;

    public function fingerprint(string $audience): string;
}
