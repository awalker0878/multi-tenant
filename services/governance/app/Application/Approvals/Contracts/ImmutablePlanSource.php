<?php

declare(strict_types=1);

namespace App\Application\Approvals\Contracts;

interface ImmutablePlanSource
{
    /** @return array<string, mixed> */
    public function fetch(string $tenant, string $planId, int $revision): array;
}
