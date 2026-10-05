<?php

declare(strict_types=1);

namespace App\Infrastructure\Messaging;

interface ConfirmedPublisher
{
    /** Return only after a routed, persistent publication is broker-confirmed. */
    public function publish(string $wire, string $eventId): void;
}
