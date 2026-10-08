<?php

declare(strict_types=1);

namespace App\Domain\Support;

final readonly class SupportTrustState
{
    /** @param list<string> $keyThumbprints */
    public function __construct(public int $connectionRevision, public array $keyThumbprints, public int $observedAt) {}
}
