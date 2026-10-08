<?php

declare(strict_types=1);

namespace App\Domain\Recovery;

final class RecoveryJson
{
    public const DOMAIN = "governance-identity-recovery-v1\n";

    public static function encode(mixed $value): string
    {
        return json_encode(self::sort($value), JSON_THROW_ON_ERROR | JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE);
    }

    public static function digest(mixed $value): string
    {
        return hash('sha256', self::encode($value));
    }

    /** @return array<string, mixed> */
    public static function decode(string $wire): array
    {
        try {
            $data = json_decode($wire, true, 32, JSON_THROW_ON_ERROR);
            // Reject ambiguous encodings, duplicate keys, trailing material and floats.
            if (! is_array($data) || array_is_list($data) || self::encode($data) !== $wire) {
                throw new RecoveryDenied;
            }

            return $data;
        } catch (\Throwable) {
            throw new RecoveryDenied;
        }
    }

    public static function hash(mixed $value): bool
    {
        return is_string($value) && preg_match('/\A[0-9a-f]{64}\z/', $value) === 1;
    }

    public static function uuid(mixed $value): bool
    {
        return is_string($value) && preg_match('/\A[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\z/', $value) === 1;
    }

    private static function sort(mixed $value): mixed
    {
        if (is_float($value) || is_object($value)) {
            throw new RecoveryDenied;
        }
        if (is_array($value)) {
            if (! array_is_list($value)) {
                ksort($value, SORT_STRING);
            }
            foreach ($value as $key => $child) {
                $value[$key] = self::sort($child);
            }
        }

        return $value;
    }
}
