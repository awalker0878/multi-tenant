<?php

declare(strict_types=1);

namespace App\Application\Messaging\Actions;

use App\Application\Messaging\Contracts\EventEncoder;
use App\Domain\Messaging\Outbox;

final class PublishGovernanceEvent
{
    public function __construct(private readonly PublishOutboxEvent $relay, private readonly EventEncoder $encoder) {}

    public function handle(): string
    {
        return $this->relay->handle(Outbox::Governance, $this->encoder);
    }
}
