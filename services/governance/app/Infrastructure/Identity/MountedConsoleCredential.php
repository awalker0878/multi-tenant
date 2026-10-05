<?php

declare(strict_types=1);

namespace App\Infrastructure\Identity;

use App\Application\Identity\Contracts\ConsoleCredential;
use App\Infrastructure\Foundation\MountedSecret;

final class MountedConsoleCredential implements ConsoleCredential
{
    public function __construct(private readonly MountedSecret $secrets) {}

    public function accepts(#[\SensitiveParameter] string $token): bool
    {
        // Read on every call: removing/replacing the mounted identity revokes it immediately.
        $expected = $this->secrets->read(config('identity.console_credential_file'));

        return is_string($expected) && strlen($expected) >= 32 && strlen($token) <= 4096 && hash_equals($expected, $token);
    }
}
