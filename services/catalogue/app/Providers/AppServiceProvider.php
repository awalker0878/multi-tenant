<?php

declare(strict_types=1);

namespace App\Providers;

use App\Application\Authorization\Contracts\ConsoleCaller;
use App\Application\Authorization\Contracts\DelegatedAuthority;
use App\Application\Authorization\Contracts\OwnerDirectory;
use App\Application\Authorization\Data\ActorContext;
use App\Application\Foundation\Contracts\DependencyProbe;
use App\Application\Foundation\Contracts\HealthCredential;
use App\Application\Foundation\Contracts\SignalBuffer;
use App\Application\IntentRevisions\Contracts\IntentValidator;
use App\Application\Messaging\Contracts\CataloguePublisher;
use App\Infrastructure\Authorization\GovernanceDelegatedAuthority;
use App\Infrastructure\Authorization\GovernanceOwnerDirectory;
use App\Infrastructure\Authorization\MountedConsoleCaller;
use App\Infrastructure\Catalogue\SchemaIntentValidator;
use App\Infrastructure\Foundation\BoundedSignalBuffer;
use App\Infrastructure\Foundation\MountedHealthCredential;
use App\Infrastructure\Foundation\PostgresDependencyProbe;
use App\Infrastructure\Messaging\RabbitCataloguePublisher;
use App\Policies\CataloguePolicy;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Support\Facades\Gate;
use Illuminate\Support\ServiceProvider;

final class AppServiceProvider extends ServiceProvider
{
    public function boot(): void
    {
        Model::preventLazyLoading();
        Model::preventSilentlyDiscardingAttributes();
        Gate::define('catalogue', function (ActorContext $actor, string $action, string $tenant, ?string $application = null, ?string $environment = null): bool {
            (new CataloguePolicy)->check($actor, $action, $tenant, $application, $environment);

            return true;
        });
    }

    public function register(): void
    {
        $this->app->bind(CataloguePublisher::class, RabbitCataloguePublisher::class);
        $this->app->bind(IntentValidator::class, SchemaIntentValidator::class);
        $this->app->bind(OwnerDirectory::class, GovernanceOwnerDirectory::class);
        $this->app->bind(ConsoleCaller::class, MountedConsoleCaller::class);
        $this->app->bind(DelegatedAuthority::class, GovernanceDelegatedAuthority::class);
        $this->app->bind(SignalBuffer::class, BoundedSignalBuffer::class);
        $this->app->bind(HealthCredential::class, MountedHealthCredential::class);
        $this->app->bind(DependencyProbe::class, PostgresDependencyProbe::class);
    }
}
