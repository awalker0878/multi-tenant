<?php

declare(strict_types=1);

namespace App\Domain\Identity;

final readonly class AdmissionState
{
    public function __construct(public string $binding, public bool $bootstrapAllowed) {}
}
