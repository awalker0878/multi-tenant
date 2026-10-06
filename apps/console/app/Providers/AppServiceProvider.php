<?php

declare(strict_types=1);

namespace App\Providers;

use App\Application\Catalogue\Contracts\CatalogueGateway;
use App\Application\Foundation\Contracts\DependencyProbe;
use App\Application\Foundation\Contracts\HealthCredential;
use App\Application\Foundation\Contracts\SignalBuffer;
use App\Application\Identity\Contracts\IdentityGateway;
use App\Application\Notifications\Contracts\NotificationDecoder;
use App\Application\Notifications\Contracts\NotificationHints;
use App\Application\Notifications\Contracts\NotificationSource;
use App\Application\Tenancy\Contracts\TenantGateway;
use App\Infrastructure\Catalogue\CatalogueClient;
use App\Infrastructure\Foundation\BoundedSignalBuffer;
use App\Infrastructure\Foundation\MountedHealthCredential;
use App\Infrastructure\Foundation\PostgresDependencyProbe;
use App\Infrastructure\Governance\GovernanceTenantGateway;
use App\Infrastructure\Identity\GovernanceIdentityGateway;
use App\Infrastructure\Notifications\GovernanceNotificationDecoder;
use App\Infrastructure\Notifications\PostgresNotificationHints;
use App\Infrastructure\Notifications\RabbitNotificationSource;
use Illuminate\Support\ServiceProvider;

final class AppServiceProvider extends ServiceProvider
{
    public function register(): void
    {
        $this->app->bind(CatalogueGateway::class, CatalogueClient::class);
        $this->app->singleton(NotificationSource::class, RabbitNotificationSource::class);
        $this->app->bind(NotificationDecoder::class, GovernanceNotificationDecoder::class);
        $this->app->bind(NotificationHints::class, PostgresNotificationHints::class);
        $this->app->bind(TenantGateway::class, GovernanceTenantGateway::class);
        $this->app->bind(IdentityGateway::class, GovernanceIdentityGateway::class);
        $this->app->bind(SignalBuffer::class, BoundedSignalBuffer::class);
        $this->app->bind(HealthCredential::class, MountedHealthCredential::class);
        $this->app->bind(DependencyProbe::class, PostgresDependencyProbe::class);
    }
}
