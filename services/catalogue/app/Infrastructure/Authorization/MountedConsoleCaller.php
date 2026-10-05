<?php

declare(strict_types=1);

namespace App\Infrastructure\Authorization;

use App\Application\Authorization\Contracts\ConsoleCaller;
use App\Infrastructure\Foundation\MountedSecret;

final class MountedConsoleCaller implements ConsoleCaller
{
    public function __construct(private readonly MountedSecret $secrets) {}

    public function accepts(#[\SensitiveParameter] string $credential): bool
    {
        $expected = $this->secrets->read(config('authorization.console_credential_file'));
        $outgoing = $this->secrets->read(config('authorization.governance_credential_file'));

        return $expected !== null && preg_match('/\A[A-Za-z0-9_-]{32,4096}\z/', $expected)
            && ($outgoing === null || ! hash_equals($expected, $outgoing)) && hash_equals($expected, $credential);
    }
}
