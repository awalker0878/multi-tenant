<?php

declare(strict_types=1);

namespace App\Application\Identity\Data;

final readonly class ConsoleSession
{
    public function __construct(#[\SensitiveParameter] public string $token, public ConsoleActor $actor) {}
}
