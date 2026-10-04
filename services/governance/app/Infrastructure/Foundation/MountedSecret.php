<?php

declare(strict_types=1);

namespace App\Infrastructure\Foundation;

final class MountedSecret
{
    public function read(mixed $path): ?string
    {
        // Absolute local files only; never permit stream wrappers or environment fallbacks.
        if (! is_string($path) || ! str_starts_with($path, '/') || str_contains($path, "\0") || ! is_file($path) || ! is_readable($path)) {
            return null;
        }

        $value = @file_get_contents($path, false, null, 0, 4097);
        if (! is_string($value) || strlen($value) > 4096) {
            return null;
        }

        $value = rtrim($value, "\r\n");

        return $value !== '' && ! preg_match('/[\x00\r\n]/', $value) ? $value : null;
    }
}
