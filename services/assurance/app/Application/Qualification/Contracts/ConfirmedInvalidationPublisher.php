<?php

declare(strict_types=1);

namespace App\Application\Qualification\Contracts;

interface ConfirmedInvalidationPublisher
{
    /**
     * Return only after an authorized downstream inbox durably acknowledges the
     * immutable event. A transport-level HTTP success alone is not acceptance.
     *
     * @param array<string, mixed> $event
     */
    public function publish(array $event): void;
}
