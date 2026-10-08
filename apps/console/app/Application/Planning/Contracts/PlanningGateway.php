<?php

declare(strict_types=1);

namespace App\Application\Planning\Contracts;

interface PlanningGateway
{
    /** @param list<string> $sites
     * @param array<string, mixed> $body
     * @return array<string, mixed> */
    public function call(string $session, string $tenant, string $application, string $environment, string $method, string $tail, array $sites, array $body = [], ?string $key = null): array;
}
