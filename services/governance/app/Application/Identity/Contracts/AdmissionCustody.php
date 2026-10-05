<?php

declare(strict_types=1);

namespace App\Application\Identity\Contracts;

use App\Domain\Identity\AdmissionState;

interface AdmissionCustody
{
    public function current(): AdmissionState;
}
