<?php

declare(strict_types=1);

namespace App\Infrastructure\Governance;

use App\Application\Tenancy\Contracts\TenantGateway;
use App\Domain\Identity\IdentityFailure;

final class GovernanceTenantGateway implements TenantGateway
{
    public function __construct(private readonly GovernanceClient $http) {}

    public function directory(#[\SensitiveParameter] string $token, ?string $tenant = null, ?string $cursor = null): array
    {
        $path = $tenant === null ? '/v1/tenant-directory' : $this->path($tenant).'/membership-directory';
        if ($cursor !== null) {
            if ($cursor === '' || strlen($cursor) > 2048) {
                throw new IdentityFailure(422);
            }
            $path .= '?'.http_build_query(['cursor' => $cursor], '', '&', PHP_QUERY_RFC3986);
        }

        return $this->http->send('GET', $path, $token);
    }

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
