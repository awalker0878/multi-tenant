<?php

declare(strict_types=1);

namespace App\Application\Authorization\Data;

final readonly class ActorContext
{
    /** @param array{site_id: ?string, environment: ?string, resource_id: ?string} $scope */
    public function __construct(public string $actorId, public string $tenantId, public string $action, public array $scope, public string $delegationId) {}
}
