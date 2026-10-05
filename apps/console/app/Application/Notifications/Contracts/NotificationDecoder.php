<?php

declare(strict_types=1);

namespace App\Application\Notifications\Contracts;

use App\Application\Notifications\Data\Delivery;
use App\Domain\Notifications\TenantNotification;

interface NotificationDecoder
{
    public function decode(Delivery $delivery): TenantNotification;
}
