<?php

declare(strict_types=1);

namespace App\Providers;

use App\Application\Approvals\Contracts\ImmutablePlanSource;
use App\Application\Foundation\Contracts\DependencyProbe;
use App\Application\Foundation\Contracts\HealthCredential;
use App\Application\Foundation\Contracts\SignalBuffer;
use App\Application\Identity\Contracts\ConsoleCredential;
use App\Application\Identity\Contracts\DeploymentTerminal;
use App\Application\Identity\Contracts\OidcHttpTransport;
use App\Application\Identity\Contracts\OidcProvider;
use App\Application\Messaging\Contracts\ConfirmedPublisher;
use App\Application\Messaging\Contracts\EventEncoder;
use App\Infrastructure\Approvals\PlanningPlanSource;
use App\Infrastructure\Foundation\BoundedSignalBuffer;
use App\Infrastructure\Foundation\MountedHealthCredential;
use App\Infrastructure\Foundation\PostgresDependencyProbe;
use App\Infrastructure\Identity\ExternalOidcProvider;
use App\Infrastructure\Identity\InteractiveDeploymentTerminal;
use App\Infrastructure\Identity\MountedConsoleCredential;
use App\Infrastructure\Identity\OidcHttpClient;
use App\Infrastructure\Messaging\GovernanceEventEncoder;
use App\Infrastructure\Messaging\RabbitPublisher;
use Illuminate\Support\ServiceProvider;

final class AppServiceProvider extends ServiceProvider
{
    public function register(): void
    {
        $this->app->bind(ConfirmedPublisher::class, RabbitPublisher::class);
        $this->app->bind(EventEncoder::class, GovernanceEventEncoder::class);
        $this->app->bind(ImmutablePlanSource::class, PlanningPlanSource::class);
        $this->app->bind(SignalBuffer::class, BoundedSignalBuffer::class);
        $this->app->bind(HealthCredential::class, MountedHealthCredential::class);
        $this->app->bind(DependencyProbe::class, PostgresDependencyProbe::class);
        $this->app->bind(ConsoleCredential::class, MountedConsoleCredential::class);
        $this->app->bind(OidcProvider::class, ExternalOidcProvider::class);
        $this->app->bind(OidcHttpTransport::class, OidcHttpClient::class);
        $this->app->bind(DeploymentTerminal::class, InteractiveDeploymentTerminal::class);
    }
}
