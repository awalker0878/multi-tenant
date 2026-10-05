<?php

declare(strict_types=1);

namespace App\Application\Identity\Data;

final readonly class LocalSession
{
    public function __construct(#[\SensitiveParameter] public string $token, public LocalActor $actor) {}
}
