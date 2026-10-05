<?php

declare(strict_types=1);

namespace App\Application\Identity\Contracts;

interface ConsoleCredential
{
    public function accepts(#[\SensitiveParameter] string $token): bool;
}
