<?php

declare(strict_types=1);

namespace App\Domain\Notifications;

final readonly class TenantNotification
{
    public function __construct(public string $id, public string $tenantId, public string $type) {}
}
