<?php

declare(strict_types=1);

namespace App\Providers;

use App\Application\Authorization\Contracts\ConsoleCaller;
use App\Application\Authorization\Contracts\DelegatedAuthority;
use App\Application\Foundation\Contracts\DependencyProbe;
use App\Application\Foundation\Contracts\HealthCredential;
use App\Application\Foundation\Contracts\SignalBuffer;
use App\Infrastructure\Authorization\GovernanceDelegatedAuthority;
use App\Infrastructure\Authorization\MountedConsoleCaller;
use App\Infrastructure\Foundation\BoundedSignalBuffer;
use App\Infrastructure\Foundation\MountedHealthCredential;
use App\Infrastructure\Foundation\PostgresDependencyProbe;
use Illuminate\Support\ServiceProvider;

final class AppServiceProvider extends ServiceProvider
{
    public function register(): void
    {
        $this->app->bind(ConsoleCaller::class, MountedConsoleCaller::class);
        $this->app->bind(DelegatedAuthority::class, GovernanceDelegatedAuthority::class);
        $this->app->bind(SignalBuffer::class, BoundedSignalBuffer::class);
        $this->app->bind(HealthCredential::class, MountedHealthCredential::class);
        $this->app->bind(DependencyProbe::class, PostgresDependencyProbe::class);
    }
}
