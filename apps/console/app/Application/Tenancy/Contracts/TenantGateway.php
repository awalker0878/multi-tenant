<?php

declare(strict_types=1);

namespace App\Application\Tenancy\Contracts;

interface TenantGateway
{
    /** @return array<string, mixed> */
    public function directory(#[\SensitiveParameter] string $token, ?string $tenant = null, ?string $cursor = null): array;

    /** @return array<string, mixed> */
    public function read(#[\SensitiveParameter] string $token, ?string $tenant = null, string $view = ''): array;

    /** @param array<string, mixed> $input
     * @return array<string, mixed>
     */
    public function write(#[\SensitiveParameter] string $token, ?string $tenant, string $operation, string $key, array $input): array;
}
