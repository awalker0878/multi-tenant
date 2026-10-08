<?php

declare(strict_types=1);

namespace App\Application\Foundation\Contracts;

interface SecretReader
{
    public function read(mixed $path): ?string;
}
