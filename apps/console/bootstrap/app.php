<?php

declare(strict_types=1);

use App\Domain\Catalogue\CatalogueFailure;
use App\Domain\Identity\IdentityFailure;
use App\Domain\Inventory\InventoryFailure;
use App\Domain\Planning\PlanningFailure;
use App\Http\Middleware\HandleInertiaRequests;
use App\Http\Middleware\PageResponseHeaders;
use App\Http\Middleware\RedactIdentityCallback;
use App\Http\Middleware\RequestTelemetry;
use App\Http\Middleware\RequireConsoleHost;
use Illuminate\Console\Scheduling\Schedule;
use Illuminate\Foundation\Application;
use Illuminate\Foundation\Configuration\Exceptions;
use Illuminate\Foundation\Configuration\Middleware;

return Application::configure(basePath: dirname(__DIR__))
    ->withRouting(
        web: __DIR__.'/../routes/web.php',
        then: function (): void {
            require __DIR__.'/../routes/health.php';
        },
    )
    ->withSchedule(function (Schedule $schedule): void {
        if (is_string(config('notifications.host'))) {
            $schedule->command('console:consume-notifications --limit=100')->everyMinute()->withoutOverlapping()->onOneServer();
        }
    })
    ->withMiddleware(function (Middleware $middleware): void {
        $middleware->prepend(RequestTelemetry::class);
        $middleware->web(prepend: [RequireConsoleHost::class], append: [RedactIdentityCallback::class, HandleInertiaRequests::class, PageResponseHeaders::class]);
    })
    ->withExceptions(function (Exceptions $exceptions): void {
        $exceptions->dontReport([PlanningFailure::class, IdentityFailure::class, CatalogueFailure::class, InventoryFailure::class]);
        $exceptions->render(function (PlanningFailure $error) {
            if (in_array($error->status, [401, 403, 404], true)) {
                return redirect('/account')->with('tenant_notice', 'Your planning access changed.');
            }

            return response('Planning is unavailable. Refresh to check the current review.', 503, ['Cache-Control' => 'no-store, private']);
        });
        $exceptions->render(function (InventoryFailure $error) {
            if (in_array($error->status, [403, 404], true)) {
                return redirect('/account')->with('tenant_notice', 'Your inventory access changed.');
            }

            return response('Inventory is temporarily unavailable. Retry to refresh the observed data.', 503, ['Cache-Control' => 'no-store, private']);
        });
        $exceptions->render(function (CatalogueFailure $error) {
            if (in_array($error->status, [403, 404], true)) {
                return redirect('/account')->with('tenant_notice', 'This application is unavailable or your access changed.');
            }

            return response('The application catalogue is unavailable. Your accepted revisions are unchanged. Please retry.', 503, ['Cache-Control' => 'no-store, private']);
        });
        $exceptions->dontFlash(['intent_json', 'intent', 'current_password', 'password', 'password_confirmation', 'client_secret', 'code', 'state']);
        $exceptions->render(function (IdentityFailure $error) {
            return response('Sign-in is temporarily unavailable. Please try again.', $error->status, ['Cache-Control' => 'no-store, private']);
        });
    })
    ->create();
