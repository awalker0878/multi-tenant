<?php

declare(strict_types=1);

namespace App\Domain\Recovery;

final readonly class RecoveryContext
{
    /** @param array<string, string|null> $workloads */
    public function __construct(
        public string $installation,
        public string $binding,
        public string $descriptor,
        public string $trust,
        public array $workloads,
        public string $code,
    ) {}
}
