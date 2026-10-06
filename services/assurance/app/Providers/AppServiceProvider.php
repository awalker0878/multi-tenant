<?php

declare(strict_types=1);

namespace App\Providers;

use App\Application\Evidence\Contracts\EvidenceAuthority;
use App\Application\Foundation\Contracts\DependencyProbe;
use App\Application\Foundation\Contracts\HealthCredential;
use App\Application\Foundation\Contracts\SignalBuffer;
use App\Infrastructure\Evidence\EvidenceOwners;
use App\Infrastructure\Foundation\BoundedSignalBuffer;
use App\Infrastructure\Foundation\MountedHealthCredential;
use App\Infrastructure\Foundation\PostgresDependencyProbe;
use App\Infrastructure\Planning\PlanningInputAuthority;
use Illuminate\Support\ServiceProvider;

final class AppServiceProvider extends ServiceProvider
{
    public function register(): void
    {
        $this->app->bind(EvidenceAuthority::class, EvidenceOwners::class);
        $this->app->bind(\App\Application\Planning\Contracts\PlanningInputAuthority::class, PlanningInputAuthority::class);
        $this->app->bind(SignalBuffer::class, BoundedSignalBuffer::class);
        $this->app->bind(HealthCredential::class, MountedHealthCredential::class);
        $this->app->bind(DependencyProbe::class, PostgresDependencyProbe::class);
    }
}
