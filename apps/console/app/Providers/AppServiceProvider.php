<?php

declare(strict_types=1);

namespace App\Providers;

use App\Application\Foundation\Contracts\DependencyProbe;
use App\Application\Foundation\Contracts\HealthCredential;
use App\Application\Foundation\Contracts\SignalBuffer;
use App\Application\Identity\Contracts\IdentityGateway;
use App\Application\Tenancy\Contracts\TenantGateway;
use App\Infrastructure\Foundation\BoundedSignalBuffer;
use App\Infrastructure\Foundation\MountedHealthCredential;
use App\Infrastructure\Foundation\PostgresDependencyProbe;
use App\Infrastructure\Governance\GovernanceTenantGateway;
use App\Infrastructure\Identity\GovernanceIdentityGateway;
use Illuminate\Support\ServiceProvider;

final class AppServiceProvider extends ServiceProvider
{
    public function register(): void
    {
        $this->app->bind(TenantGateway::class, GovernanceTenantGateway::class);
        $this->app->bind(IdentityGateway::class, GovernanceIdentityGateway::class);
        $this->app->bind(SignalBuffer::class, BoundedSignalBuffer::class);
        $this->app->bind(HealthCredential::class, MountedHealthCredential::class);
        $this->app->bind(DependencyProbe::class, PostgresDependencyProbe::class);
    }
}
