<?php

declare(strict_types=1);

namespace App\Application\Support\Contracts;

use App\Domain\Support\SupportTrustState;

interface SupportTrust
{
    public function current(): SupportTrustState;
}
