<?php

declare(strict_types=1);

namespace App\Application\Jobs\Contracts;

interface JobsGateway
{
    /** @param array{site_id: string, environment: string, resource_id: string} $scope
     * @param array<string, mixed> $body
     * @return array<string, mixed> */
    public function call(string $session, string $tenant, array $scope, string $method, string $tail, array $body = [], ?string $key = null): array;
}
