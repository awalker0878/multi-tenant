<?php

declare(strict_types=1);

namespace App\Domain\IntentRevisions;

use RuntimeException;

final class IntentFailure extends RuntimeException
{
    public function __construct(public readonly string $reason, public readonly int $status = 422, public readonly string $field = 'intent')
    {
        parent::__construct($reason);
    }
}
