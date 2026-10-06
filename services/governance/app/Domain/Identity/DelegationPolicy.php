<?php

declare(strict_types=1);

namespace App\Domain\Identity;

final class DelegationPolicy
{
    // Data-facing service delegation only. Native admission and administrative
    // authority require their own exact-plan/exception contracts.
    /** @var array<string, list<string>> */
    public const ACTIONS = [
        'catalogue' => ['application.read', 'application.write', 'reference.read', 'reference.write'],
        'planning' => ['plan.read', 'plan.create'],
        'assurance' => ['evidence.read'],
    ];

    public static function permits(string $audience, string $action): bool
    {
        return in_array($action, self::ACTIONS[$audience] ?? [], true);
    }
}
