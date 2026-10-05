<?php

declare(strict_types=1);

namespace App\Console\Commands;

use App\Application\Identity\Actions\BootstrapAdministrator;
use App\Application\Identity\Contracts\DeploymentTerminal;
use Illuminate\Console\Command;

final class BootstrapIdentity extends Command
{
    protected $signature = 'identity:bootstrap {--console-url= : Public HTTPS console URL (HTTP only for loopback development)}';

    protected $description = 'Create the installation administrator once and display its temporary password on the deployment terminal';

    public function handle(BootstrapAdministrator $bootstrap, DeploymentTerminal $terminal): int
    {
        $url = $this->option('console-url');
        $parts = is_string($url) && filter_var($url, FILTER_VALIDATE_URL) ? parse_url($url) : false;
        if (! is_array($parts) || isset($parts['user']) || isset($parts['pass']) || isset($parts['query']) || isset($parts['fragment'])
            || ! isset($parts['host']) || ! in_array($parts['scheme'] ?? '', ['http', 'https'], true)
            || ($parts['scheme'] === 'http' && ! in_array($parts['host'], ['localhost', '127.0.0.1', '[::1]'], true))) {
            $this->error('Supply a valid HTTPS console URL; HTTP is permitted only for loopback development.');

            return self::FAILURE;
        }
        if (! $this->input->isInteractive() || ! $terminal->isInteractive()) {
            $this->error('Run from an authorized interactive terminal with session recording disabled. Redirected and CI output are refused.');

            return self::FAILURE;
        }
        $temporary = $bootstrap->handle();
        if ($temporary === null) {
            $this->info('Bootstrap is already complete. No account or credential was changed.');

            return self::SUCCESS;
        }
        $terminal->display((string) $url, $temporary);
        unset($temporary);

        return self::SUCCESS;
    }
}
