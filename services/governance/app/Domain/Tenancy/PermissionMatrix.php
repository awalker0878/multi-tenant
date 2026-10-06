<?php

declare(strict_types=1);

namespace App\Domain\Tenancy;

final class PermissionMatrix
{
    /** @var array<string, list<string>> */
    public const ROLES = [
        'tenant_admin' => ['reference.read', 'reference.write', 'tenant.read', 'tenant.manage', 'membership.manage', 'grant.manage', 'quota.read', 'quota.manage', 'audit.read'],
        'author' => ['reference.read', 'tenant.read', 'quota.read', 'application.read', 'application.write', 'plan.read', 'plan.create', 'approval.request'],
        'reviewer' => ['reference.read', 'tenant.read', 'quota.read', 'application.read', 'plan.read', 'approval.decide', 'approval.revoke', 'evidence.read'],
        'operator' => ['reference.read', 'tenant.read', 'quota.read', 'application.read', 'plan.read', 'operation.admit', 'evidence.read'],
        'reader' => ['reference.read', 'tenant.read', 'quota.read', 'application.read', 'plan.read', 'evidence.read'],
    ];

    /** Explicit grants cannot delegate administrative or support authority. @var list<string> */
    public const DELEGABLE = ['application.read', 'application.write', 'plan.read', 'plan.create', 'approval.request', 'approval.decide', 'approval.revoke', 'operation.admit', 'evidence.read'];

    /** @param array{site_id?: string|null, environment?: string|null, resource_id?: string|null} $requested */
    public static function within(?string $site, ?string $environment, ?string $resource, array $requested): bool
    {
        return ($site === null || $site === ($requested['site_id'] ?? null))
            && ($environment === null || $environment === ($requested['environment'] ?? null))
            && ($resource === null || $resource === ($requested['resource_id'] ?? null));
    }
}
