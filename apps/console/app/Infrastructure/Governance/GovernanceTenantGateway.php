<?php

declare(strict_types=1);

namespace App\Infrastructure\Governance;

use App\Application\Tenancy\Contracts\TenantGateway;
use App\Domain\Identity\IdentityFailure;

final class GovernanceTenantGateway implements TenantGateway
{
    public function __construct(private readonly GovernanceClient $http) {}

    public function read(#[\SensitiveParameter] string $token, ?string $tenant = null, string $view = ''): array
    {
        if (! in_array($view, ['', 'memberships', 'grants', 'quota', 'audit'], true)) {
            throw new IdentityFailure(403);
        }

        return $this->http->send('GET', $this->path($tenant).($view === '' ? '' : '/'.$view), $token);
    }

    public function write(#[\SensitiveParameter] string $token, ?string $tenant, string $operation, string $key, array $input): array
    {
        if (! in_array($operation, ['', 'memberships', 'grants', 'grant-revocations', 'quota', 'state'], true)) {
            throw new IdentityFailure(403);
        }

        return $this->http->send('POST', $this->path($tenant).($operation === '' ? '' : '/'.$operation), $token, $input, $key);
    }

    private function path(?string $tenant): string
    {
        if ($tenant !== null && ! preg_match('/\A[0-9a-f-]{36}\z/', $tenant)) {
            throw new IdentityFailure(404);
        }

        return '/v1/tenants'.($tenant === null ? '' : '/'.$tenant);
    }
}
