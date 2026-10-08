<?php

declare(strict_types=1);

namespace App\Infrastructure\Session;

use Illuminate\Contracts\Cache\Lock;
use Illuminate\Contracts\Cache\LockProvider;
use Illuminate\Contracts\Cache\Repository;
use InvalidArgumentException;

// Caller supplies freshly authorized tenant scope on every operation.
final readonly class TenantCache
{
    public function __construct(private Repository $cache, private LockProvider $locks) {}

    public function put(string $tenant, string $key, string $value, int $seconds): void
    {
        if ($seconds < 1 || $seconds > 1800) {
            throw new InvalidArgumentException('Invalid tenant cache lifetime');
        }
        $this->cache->put($this->key($tenant, $key), $value, $seconds);
    }

    public function get(string $tenant, string $key): mixed
    {
        return $this->cache->get($this->key($tenant, $key));
    }

    public function lock(string $tenant, string $key, int $seconds): Lock
    {
        if ($seconds < 1 || $seconds > 30) {
            throw new InvalidArgumentException('Invalid tenant lock lifetime');
        }

        return $this->locks->lock($this->key($tenant, $key), $seconds);
    }

    private function key(string $tenant, string $key): string
    {
        if (! preg_match('/\A[a-z][a-z0-9_-]{0,63}\z/', $tenant) || $key === '' || strlen($key) > 256) {
            throw new InvalidArgumentException('Invalid tenant cache scope');
        }

        return 'tenant:'.$tenant.':'.hash('sha256', $key);
    }
}
