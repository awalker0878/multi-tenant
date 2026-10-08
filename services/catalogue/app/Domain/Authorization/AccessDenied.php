<?php

declare(strict_types=1);

namespace App\Domain\Authorization;

final class AccessDenied extends \RuntimeException
{
    public function __construct(public readonly int $status = 403)
    {
        parent::__construct('access_unavailable');
    }
}
