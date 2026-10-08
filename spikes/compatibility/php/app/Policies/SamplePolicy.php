<?php

declare(strict_types=1);

namespace App\Policies;

use App\Domain\Compatibility\Models\Actor;
use App\Domain\Compatibility\Models\Sample;

final class SamplePolicy
{
    public function viewAny(Actor $actor): bool
    {
        return in_array($actor->role, ['reader', 'editor'], true);
    }

    public function approve(Actor $actor, Sample $sample): bool
    {
        return $actor->tenant_id === $sample->tenant_id && $actor->role === 'editor';
    }
}
