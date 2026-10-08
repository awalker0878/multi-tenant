<?php

declare(strict_types=1);

namespace App\Domain\Inventory;

final class InventoryFailure extends \RuntimeException
{
    public function __construct(public readonly int $status = 503, public readonly string $reason = 'inventory_unavailable')
    {
        parent::__construct($reason);
    }
}
