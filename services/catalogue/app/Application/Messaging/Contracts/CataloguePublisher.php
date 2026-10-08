<?php

declare(strict_types=1);

namespace App\Application\Messaging\Contracts;

interface CataloguePublisher
{
    public function publish(string $wire, string $eventId): void;
}
