<?php

declare(strict_types=1);

namespace App\Application\Authorization\Contracts;

use App\Application\Authorization\Data\ActorContext;

interface DelegatedAuthority
{
    /** @param array{site_id: ?string, environment: ?string, resource_id: ?string} $scope */
    public function check(#[\SensitiveParameter] string $token, string $tenant, string $action, array $scope): ActorContext;
}
