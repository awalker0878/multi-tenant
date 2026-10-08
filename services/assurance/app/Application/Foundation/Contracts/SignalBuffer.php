<?php

declare(strict_types=1);

namespace App\Application\Foundation\Contracts;

interface SignalBuffer
{
    /** @param array<string, mixed> $record */
    public function append(array $record): string;
}
