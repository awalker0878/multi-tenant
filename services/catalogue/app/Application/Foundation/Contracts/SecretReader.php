<?php

declare(strict_types=1);

namespace App\Application\Foundation\Contracts;

/** Read the current mounted secret without coupling HTTP delivery to local files. */
interface SecretReader
{
    public function read(mixed $path): ?string;
}
