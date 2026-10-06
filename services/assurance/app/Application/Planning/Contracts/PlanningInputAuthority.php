<?php

declare(strict_types=1);

namespace App\Application\Planning\Contracts;

interface PlanningInputAuthority
{
    /** @param array<string, list<string|null>> $headers
     * @param array{site_id: string, environment: string, resource_id: string} $scope
     * @return array<string, mixed> */
    public function check(array $headers, string $tenant, array $scope): array;
}
