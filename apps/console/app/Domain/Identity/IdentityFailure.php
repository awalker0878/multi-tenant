<?php

declare(strict_types=1);

namespace App\Domain\Identity;

use RuntimeException;

final class IdentityFailure extends RuntimeException
{
    public function __construct(public readonly int $status)
    {
        parent::__construct('Identity request could not be completed.');
    }
}
