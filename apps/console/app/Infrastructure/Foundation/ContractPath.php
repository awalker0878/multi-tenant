<?php

declare(strict_types=1);

namespace App\Infrastructure\Foundation;

use InvalidArgumentException;

final class ContractPath
{
    public static function bind(string $template, string $tenant, array $parameters): string
    {
        preg_match_all('/\{([^}]+)\}/', $template, $matches);
        $required = array_values(array_diff($matches[1], ['tenant']));
        if (array_diff(array_keys($parameters), $required) !== []) {
            throw new InvalidArgumentException('unexpected_identity');
        }
        if (array_diff($required, array_keys($parameters)) !== []) {
            throw new InvalidArgumentException('missing_identity');
        }
        $values = ['tenant' => $tenant, ...$parameters];
        foreach ($values as $field => $value) {
            if (! is_string($value) || ! preg_match('/\A[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}\z/', $value)) {
                throw new InvalidArgumentException('invalid_identity');
            }
            $template = str_replace('{'.$field.'}', $value, $template);
        }

        return $template;
    }
}
