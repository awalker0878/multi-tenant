<?php

declare(strict_types=1);

namespace App\Infrastructure\Identity;

use App\Application\Identity\Contracts\DeploymentTerminal;
use RuntimeException;

final class InteractiveDeploymentTerminal implements DeploymentTerminal
{
    public function isInteractive(): bool
    {
        return PHP_SAPI === 'cli' && defined('STDIN') && defined('STDOUT') && stream_isatty(STDIN) && stream_isatty(STDOUT);
    }

    public function display(string $consoleUrl, #[\SensitiveParameter] string $temporaryPassword): void
    {
        if (! $this->isInteractive()) {
            throw new RuntimeException('An authorized interactive deployment terminal is required.');
        }
        // Deliberately outside application logging, events and command output capture.
        fwrite(STDOUT, "Console: {$consoleUrl}\nAccount: admin\nTemporary password: {$temporaryPassword}\nChange this password at first sign-in. It will not be displayed again.\n");
    }
}
