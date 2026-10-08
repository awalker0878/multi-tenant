<?php

declare(strict_types=1);

namespace App\Application\Messaging\Actions;

use App\Application\Messaging\Contracts\FactWriter;

// Internal foundation entrypoint. No HTTP route or user authorization is implied.
final readonly class RecordFoundationFact
{
    public function __construct(private FactWriter $writer) {}

    public function handle(string $wire, string $payload, string $trustedTenant, string $trustedActor): string
    {
        return $this->writer->append($wire, $payload, $trustedTenant, $trustedActor);
    }
}
