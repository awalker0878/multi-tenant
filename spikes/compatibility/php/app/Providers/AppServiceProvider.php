<?php

declare(strict_types=1);

namespace App\Providers;

use App\Domain\Compatibility\Models\Sample;
use App\Policies\SamplePolicy;
use Illuminate\Support\Facades\Gate;
use Illuminate\Support\ServiceProvider;

final class AppServiceProvider extends ServiceProvider
{
    public function boot(): void
    {
        Gate::policy(Sample::class, SamplePolicy::class);
    }
}
