<?php

declare(strict_types=1);

namespace App\Application\Identity\Data;

final readonly class LocalActor
{
    public function __construct(public bool $passwordChangeRequired) {}
}
