<?php

declare(strict_types=1);

namespace App\Application\Notifications\Contracts;

use App\Application\Notifications\Data\Delivery;
use App\Domain\Notifications\CommittedNotification;

interface NotificationDecoder
{
    public function decode(Delivery $delivery): CommittedNotification;
}
