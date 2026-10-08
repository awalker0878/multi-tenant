<?php

declare(strict_types=1);

namespace App\Policies;

use App\Application\Authorization\Data\ActorContext;
use App\Domain\Authorization\AccessDenied;

final class CataloguePolicy
{
    public function check(ActorContext $actor, string $action, string $tenant, ?string $application = null, ?string $environment = null): void
    {
        if ($actor->tenantId !== $tenant || $actor->action !== $action
            || $actor->scope['site_id'] !== null
            || ($actor->scope['environment'] !== null && $actor->scope['environment'] !== $environment)
            || ($actor->scope['resource_id'] !== null && $actor->scope['resource_id'] !== $application)) {
            throw new AccessDenied;
        }
    }
}
