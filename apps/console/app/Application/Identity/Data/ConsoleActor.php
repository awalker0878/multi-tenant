<?php

declare(strict_types=1);

namespace App\Application\Identity\Data;

final readonly class ConsoleActor
{
    public function __construct(public bool $passwordChangeRequired, public string $subject = 'bootstrap-admin', public bool $federated = false, public bool $installationAdministrator = false) {}
}
