<?php

declare(strict_types=1);

namespace App\Providers;

use App\Application\Approvals\Contracts\ImmutablePlanSource;
use App\Application\Foundation\Contracts\DependencyProbe;
use App\Application\Foundation\Contracts\HealthCredential;
use App\Application\Foundation\Contracts\SignalBuffer;
use App\Application\Identity\Contracts\AdmissionCustody;
use App\Application\Identity\Contracts\ConsoleCredential;
use App\Application\Identity\Contracts\DeploymentTerminal;
use App\Application\Identity\Contracts\OidcHttpTransport;
use App\Application\Identity\Contracts\OidcProvider;
use App\Application\Identity\Contracts\ServiceCredentials;
use App\Application\Messaging\Actions\PublishIdentityEvent;
use App\Application\Messaging\Actions\PublishSupportEvent;
use App\Application\Messaging\Contracts\ConfirmedPublisher;
use App\Application\Messaging\Contracts\EventEncoder;
use App\Application\Support\Contracts\SupportTrust;
use App\Infrastructure\Approvals\PlanningPlanSource;
use App\Infrastructure\Foundation\BoundedSignalBuffer;
use App\Infrastructure\Foundation\MountedHealthCredential;
use App\Infrastructure\Foundation\PostgresDependencyProbe;
use App\Infrastructure\Identity\ExternalOidcProvider;
use App\Infrastructure\Identity\InteractiveDeploymentTerminal;
use App\Infrastructure\Identity\MountedAdmissionCustody;
use App\Infrastructure\Identity\MountedConsoleCredential;
use App\Infrastructure\Identity\MountedServiceCredentials;
use App\Infrastructure\Identity\OidcHttpClient;
use App\Infrastructure\Messaging\GovernanceEventEncoder;
use App\Infrastructure\Messaging\IdentityEventEncoder;
use App\Infrastructure\Messaging\RabbitPublisher;
use App\Infrastructure\Messaging\SupportEventEncoder;
use App\Infrastructure\Support\OnlineSupportTrust;
use Illuminate\Support\ServiceProvider;

final class AppServiceProvider extends ServiceProvider
{
    public function register(): void
    {
        $this->app->bind(ConfirmedPublisher::class, RabbitPublisher::class);
        $this->app->bind(SupportTrust::class, OnlineSupportTrust::class);
        $this->app->bind(EventEncoder::class, GovernanceEventEncoder::class);
        $this->app->when(PublishIdentityEvent::class)->needs(EventEncoder::class)->give(IdentityEventEncoder::class);
        $this->app->when(PublishSupportEvent::class)->needs(EventEncoder::class)->give(SupportEventEncoder::class);
        $this->app->bind(ImmutablePlanSource::class, PlanningPlanSource::class);
        $this->app->bind(SignalBuffer::class, BoundedSignalBuffer::class);
        $this->app->bind(HealthCredential::class, MountedHealthCredential::class);
        $this->app->bind(DependencyProbe::class, PostgresDependencyProbe::class);
        $this->app->bind(AdmissionCustody::class, MountedAdmissionCustody::class);
        $this->app->bind(ConsoleCredential::class, MountedConsoleCredential::class);
        $this->app->bind(ServiceCredentials::class, MountedServiceCredentials::class);
        $this->app->bind(OidcProvider::class, ExternalOidcProvider::class);
        $this->app->bind(OidcHttpTransport::class, OidcHttpClient::class);
        $this->app->bind(DeploymentTerminal::class, InteractiveDeploymentTerminal::class);
    }
}
