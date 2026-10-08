<?php

declare(strict_types=1);

namespace App\Application\Notifications\Contracts;

interface NotificationHints
{
    public function current(string $tenant): ?string;
}
