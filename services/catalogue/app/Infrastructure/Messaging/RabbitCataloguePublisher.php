<?php

declare(strict_types=1);

namespace App\Infrastructure\Messaging;

use App\Application\Messaging\Contracts\CataloguePublisher;
use App\Infrastructure\Foundation\MountedSecret;
use RuntimeException;

final class RabbitCataloguePublisher implements CataloguePublisher
{
    public function __construct(private readonly MountedSecret $secrets) {}

    public function publish(string $wire, string $eventId): void
    {
        $host = config('catalogue.broker_host');
        $port = config('catalogue.broker_port');
        $ca = config('catalogue.broker_ca_file');
        $password = $this->secrets->read(config('catalogue.broker_password_file'));
        if (! is_string($host) || ! preg_match('/\A[A-Za-z0-9_.:-]{1,253}\z/', $host) || ! is_numeric($port) || (int) $port < 1 || (int) $port > 65535
          || ! is_string($ca) || ! str_starts_with($ca, '/') || ! is_readable($ca) || $password === null) {
            throw new RuntimeException('publication_unavailable');
        }
        (new RabbitPublisher($host, $password, $ca, 'catalogue.intent.changed.v1', (int) $port))->publish($wire, $eventId);
    }
}
