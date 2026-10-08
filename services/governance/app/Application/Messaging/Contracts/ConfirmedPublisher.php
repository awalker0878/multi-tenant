<?php

declare(strict_types=1);

namespace App\Application\Messaging\Contracts;

interface ConfirmedPublisher
{
    /** Return only after a routed, persistent message is broker-confirmed. */
    public function publish(string $wire, string $eventId, string $routingKey): void;
}
