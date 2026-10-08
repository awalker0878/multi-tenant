<?php

declare(strict_types=1);

namespace App\Infrastructure\Foundation;

use App\Application\Foundation\Contracts\HealthCredential;
use Illuminate\Contracts\Config\Repository;

final class MountedHealthCredential implements HealthCredential
{
    public function __construct(
        private readonly Repository $config,
        private readonly MountedSecret $secrets,
    ) {}

    public function accepts(?string $credential): bool
    {
        if ($credential === null || ! preg_match('/\A[\x21-\x7e]{32,4096}\z/', $credential)) {
            return false;
        }

        // Re-read on every call so replacing/revoking the file needs no process restart.
        $expected = $this->secrets->read($this->config->get('foundation.health_token_file'));

        return $expected !== null && strlen($expected) >= 32 && hash_equals($expected, $credential);
    }
}
