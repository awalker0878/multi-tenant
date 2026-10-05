<?php

declare(strict_types=1);

namespace App\Application\Messaging\Contracts;

interface FactWriter
{
    public function append(string $wire, string $payload, string $tenant, string $actor): string;
}
