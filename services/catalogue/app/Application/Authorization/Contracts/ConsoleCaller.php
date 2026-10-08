<?php

declare(strict_types=1);

namespace App\Application\Authorization\Contracts;

interface ConsoleCaller
{
    public function accepts(#[\SensitiveParameter] string $credential): bool;
}
