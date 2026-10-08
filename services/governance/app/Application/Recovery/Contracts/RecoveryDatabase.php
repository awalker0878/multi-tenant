<?php

declare(strict_types=1);

namespace App\Application\Recovery\Contracts;

use App\Domain\Support\SupportTrustState;
use Closure;

interface RecoveryDatabase
{
    /** @param Closure(): SupportTrustState $read */
    public function observe(Closure $read): SupportTrustState;

    /** Acquire migration-owner authority and exclusive locks; never available to runtime. */
    public function lock(): void;

    /** @return list<string> */
    public function tables(): array;
}
