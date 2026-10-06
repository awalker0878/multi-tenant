<?php

declare(strict_types=1);

namespace App\Domain\Planning;

final class PlanningFailure extends \RuntimeException
{
    public function __construct(public readonly int $status = 503, public readonly string $reason = 'planning_unavailable')
    {
        parent::__construct($reason);
    }
}
