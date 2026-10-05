<?php

declare(strict_types=1);

namespace App\Domain\Identity;

final class OidcUrl
{
    public static function origin(string $url, bool $callback = false): string
    {
        $parts = filter_var($url, FILTER_VALIDATE_URL) ? parse_url($url) : false;
        if (! is_array($parts) || ! isset($parts['host'], $parts['scheme']) || isset($parts['user']) || isset($parts['pass'])
            || isset($parts['query']) || isset($parts['fragment']) || preg_match('/[\x00-\x20\x7f\\\\]/', $url)
            || ($parts['scheme'] !== 'https' && ! ($callback && $parts['scheme'] === 'http' && $parts['host'] === '127.0.0.1'))
            || ($callback && ($parts['path'] ?? '') !== '/identity/callback')) {
            throw new IdentityDenied('invalid_oidc_url', 422);
        }

        return $parts['scheme'].'://'.strtolower($parts['host']).':'.($parts['port'] ?? ($parts['scheme'] === 'https' ? 443 : 80));
    }
}
