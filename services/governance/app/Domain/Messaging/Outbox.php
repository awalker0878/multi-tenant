<?php

declare(strict_types=1);

namespace App\Domain\Messaging;

enum Outbox: string
{
    case Governance = 'app.governance_outbox';
    case Identity = 'app.identity_outbox';
    case Support = 'app.support_outbox';
}
