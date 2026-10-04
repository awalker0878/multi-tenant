<?php

declare(strict_types=1);

namespace App\Application\Foundation\Actions;

use App\Application\Foundation\Contracts\DependencyProbe;
use App\Application\Foundation\Contracts\HealthCredential;
use App\Application\Foundation\Data\DependencyStatus;

final class InspectDependencies
{
    public function __construct(
        private readonly HealthCredential $credentials,
        private readonly DependencyProbe $dependencies,
    ) {}

    public function handle(?string $credential): DependencyStatus
    {
        // A probe credential never establishes a product actor or tenant authority.
        if (! $this->credentials->accepts($credential)) {
            return DependencyStatus::Unauthorized;
        }

        return $this->dependencies->healthy() ? DependencyStatus::Ready : DependencyStatus::Unavailable;
    }
}
