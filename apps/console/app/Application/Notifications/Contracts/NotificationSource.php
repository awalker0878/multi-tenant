<?php

declare(strict_types=1);

namespace App\Application\Notifications\Contracts;

use App\Application\Notifications\Data\Delivery;

interface NotificationSource
{
    public function next(): ?Delivery;

    public function acknowledge(): void;

    public function close(): void;
}
