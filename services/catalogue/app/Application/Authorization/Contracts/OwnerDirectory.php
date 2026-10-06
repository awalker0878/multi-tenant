<?php

declare(strict_types=1);

namespace App\Application\Authorization\Contracts;

use App\Application\Authorization\Data\ActorContext;

interface OwnerDirectory
{
    /**
     * @param list<string> $owners */
    public function assertOwners(ActorContext $actor, array $owners): void;
}
