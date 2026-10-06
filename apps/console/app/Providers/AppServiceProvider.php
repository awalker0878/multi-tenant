<?php

declare(strict_types=1);

namespace App\Providers;

use App\Application\Catalogue\Contracts\CatalogueGateway;
use App\Application\Foundation\Contracts\DependencyProbe;
use App\Application\Foundation\Contracts\HealthCredential;
use App\Application\Foundation\Contracts\SignalBuffer;
use App\Application\Identity\Contracts\IdentityGateway;
use App\Application\Inventory\Contracts\InventoryGateway;
use App\Application\Jobs\Contracts\JobsGateway;
use App\Application\Notifications\Contracts\NotificationDecoder;
use App\Application\Notifications\Contracts\NotificationHints;
use App\Application\Notifications\Contracts\NotificationSource;
use App\Application\Planning\Contracts\ApprovalGateway;
use App\Application\Planning\Contracts\PlanningGateway;
use App\Application\Tenancy\Contracts\TenantGateway;
use App\Infrastructure\Catalogue\CatalogueClient;
use App\Infrastructure\Foundation\BoundedSignalBuffer;
use App\Infrastructure\Foundation\MountedHealthCredential;
use App\Infrastructure\Foundation\PostgresDependencyProbe;
use App\Infrastructure\Governance\GovernanceTenantGateway;
use App\Infrastructure\Identity\GovernanceIdentityGateway;
use App\Infrastructure\Inventory\InventoryClient;
use App\Infrastructure\Jobs\JobsClient;
use App\Infrastructure\Notifications\GovernanceNotificationDecoder;
use App\Infrastructure\Notifications\PostgresNotificationHints;
use App\Infrastructure\Notifications\RabbitNotificationSource;
use App\Infrastructure\Planning\GovernanceApprovals;
use App\Infrastructure\Planning\PlanningClient;
use Illuminate\Support\ServiceProvider;

final class AppServiceProvider extends ServiceProvider
{
    public function register(): void
    {
        $this->app->bind(JobsGateway::class, JobsClient::class);
        $this->app->bind(ApprovalGateway::class, GovernanceApprovals::class);
        $this->app->bind(PlanningGateway::class, PlanningClient::class);
        $this->app->bind(InventoryGateway::class, InventoryClient::class);
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
