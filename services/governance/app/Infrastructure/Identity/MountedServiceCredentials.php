<?php

declare(strict_types=1);

namespace App\Infrastructure\Identity;

use App\Application\Identity\Contracts\ServiceCredentials;
use App\Domain\Identity\DelegationPolicy;
use App\Domain\Identity\IdentityDenied;
use App\Infrastructure\Foundation\MountedSecret;

final class MountedServiceCredentials implements ServiceCredentials
{
    public function __construct(private readonly MountedSecret $secrets) {}

    public function authenticate(#[\SensitiveParameter] string $token): string
    {
        if (! preg_match('/\A[A-Za-z0-9_-]{32,4096}\z/', $token)) {
            throw new IdentityDenied('invalid_workload_identity');
        }
        $matched = [];
        foreach (array_keys(DelegationPolicy::ACTIONS) as $audience) {
            $expected = $this->read($audience);
            if ($expected !== null && hash_equals($expected, $token)) {
                $matched[] = $audience;
            }
        }
        $console = $this->read('console');
        if (count($matched) !== 1 || ($console !== null && hash_equals($console, $token))) {
            throw new IdentityDenied('invalid_workload_identity');
        }

        return $matched[0];
    }

    public function fingerprint(string $audience): string
    {
        $credential = $this->read($audience);
        if ($credential === null || ($audience !== 'console' && $this->authenticate($credential) !== $audience)) {
            throw new IdentityDenied('identity_unavailable', 503);
        }

        return hash('sha256', $credential);
    }

    private function read(string $audience): ?string
    {
        $path = $audience === 'console' ? config('identity.console_credential_file') : config('identity.service_credentials.'.$audience);
        $credential = $this->secrets->read($path);

        return $credential !== null && preg_match('/\A[A-Za-z0-9_-]{32,4096}\z/', $credential) ? $credential : null;
    }
}
