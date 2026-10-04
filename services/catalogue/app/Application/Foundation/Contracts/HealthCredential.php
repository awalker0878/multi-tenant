<?php

declare(strict_types=1);

namespace App\Application\Foundation\Contracts;

interface HealthCredential
{
    public function accepts(?string $credential): bool;
}
