<?php

declare(strict_types=1);

namespace Tests\Support;

use App\Application\Approvals\Contracts\ImmutablePlanSource;
use App\Domain\Identity\IdentityDenied;

final class SyntheticPlanSource implements ImmutablePlanSource
{
    public bool $unavailable = false;

    public function __construct(public array $plan) {}

    public function fetch(string $planId, int $revision): array
    {
        if ($this->unavailable || $planId !== $this->plan['plan_id'] || $revision !== $this->plan['revision']) {
            throw new IdentityDenied('plan_authority_unavailable', 503);
        }

        return $this->plan;
    }
}
