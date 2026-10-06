<?php

declare(strict_types=1);

namespace App\Domain\Jobs;

final class JobsFailure extends \RuntimeException
{
    public function __construct(public readonly int $status = 503, public readonly string $reason = 'jobs_unavailable')
    {
        parent::__construct($reason);
    }
}
