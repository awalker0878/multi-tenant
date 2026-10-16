<?php

declare(strict_types=1);

namespace App\Domain\Qualification;

/** Closed request values required by the current signed qualification wire. */
final class QualificationScope
{
    /** @param array<string, mixed> $scope */
    public static function valid(array $scope): bool
    {
        $required = ['tenant_id', 'site_id', 'endpoint_id', 'native_scope', 'installed_tuple', 'action', 'method', 'profile_digest', 'artifacts'];
        if (count($scope) !== count($required) || array_diff($required, array_keys($scope)) !== []) {
            return false;
        }
        foreach (['tenant_id', 'site_id', 'endpoint_id'] as $field) {
            if (! is_string($scope[$field]) || preg_match('/\A[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\z/', $scope[$field]) !== 1) {
                return false;
            }
        }
        foreach (['native_scope' => 1024, 'method' => 128] as $field => $maximum) {
            if (! is_string($scope[$field]) || preg_match('/\A.{1,'.$maximum.'}\z/us', $scope[$field]) !== 1) {
                return false;
            }
        }
        if (! in_array($scope['action'], ['application.provision', 'application.migrate', 'application.recover', 'application.retire'], true)
            || ! is_array($scope['installed_tuple']) || array_is_list($scope['installed_tuple'])
            || ! is_string($scope['profile_digest']) || preg_match('/\A[a-f0-9]{64}\z/', $scope['profile_digest']) !== 1
            || ! is_array($scope['artifacts']) || count($scope['artifacts']) !== 4
            || array_diff(['compiler', 'adapter', 'automation', 'contracts'], array_keys($scope['artifacts'])) !== []) {
            return false;
        }
        foreach ($scope['artifacts'] as $digest) {
            if (! is_string($digest) || preg_match('/\A[a-f0-9]{64}\z/', $digest) !== 1) {
                return false;
            }
        }

        return true;
    }
}
