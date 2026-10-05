<?php

declare(strict_types=1);

namespace App\Domain\Approvals;

use App\Domain\Identity\IdentityDenied;
use App\Domain\Tenancy\GovernanceLedger;
use Illuminate\Support\Str;

final readonly class BoundPlan
{
    /** @param array<string, mixed> $binding */
    private function __construct(public array $binding, public string $digest) {}

    /** @param array<string, mixed> $response */
    public static function fromArray(array $response): self
    {
        $digest = $response['digest'] ?? null;
        unset($response['digest']);
        $keys = ['plan_id', 'revision', 'tenant_id', 'action', 'site_id', 'environment', 'resource_id', 'requested_by', 'executor_ids', 'valid_until'];
        if (count($response) !== count($keys) || array_diff($keys, array_keys($response)) !== []
            || ! is_string($digest) || ! preg_match('/\A[0-9a-f]{64}\z/', $digest)
            || ! is_int($response['revision']) || $response['revision'] < 1 || ! is_int($response['valid_until'])
            || ! in_array($response['action'], ['application.provision', 'application.migrate', 'application.recover', 'application.retire'], true)
            || ! is_array($response['executor_ids']) || ! array_is_list($response['executor_ids']) || count($response['executor_ids']) < 1 || count($response['executor_ids']) > 32) {
            throw new IdentityDenied('invalid_plan_binding', 422);
        }
        foreach (['plan_id', 'tenant_id', 'requested_by'] as $key) {
            if (! is_string($response[$key]) || ! Str::isUuid($response[$key])) {
                throw new IdentityDenied('invalid_plan_binding', 422);
            }
        }
        foreach ($response['executor_ids'] as $executor) {
            if (! is_string($executor) || ! Str::isUuid($executor)) {
                throw new IdentityDenied('invalid_plan_binding', 422);
            }
        }
        foreach (['site_id', 'environment', 'resource_id'] as $key) {
            if (! is_string($response[$key]) || ! preg_match('/\A[A-Za-z0-9._:-]{1,128}\z/', $response[$key])) {
                throw new IdentityDenied('invalid_plan_binding', 422);
            }
        }
        if (! hash_equals(GovernanceLedger::digest($response), $digest)) {
            throw new IdentityDenied('plan_digest_mismatch', 409);
        }

        return new self($response, $digest);
    }

    /** @return array{site_id: string, environment: string, resource_id: string} */
    public function scope(): array
    {
        return ['site_id' => $this->binding['site_id'], 'environment' => $this->binding['environment'], 'resource_id' => $this->binding['resource_id']];
    }

    /** @return array<string, mixed> */
    public function toArray(): array
    {
        return $this->binding + ['digest' => $this->digest];
    }
}
