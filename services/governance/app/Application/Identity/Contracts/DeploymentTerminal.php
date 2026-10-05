<?php

declare(strict_types=1);

namespace App\Application\Identity\Contracts;

interface DeploymentTerminal
{
    public function isInteractive(): bool;

    public function display(string $consoleUrl, #[\SensitiveParameter] string $temporaryPassword): void;
}
