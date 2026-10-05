<?php

declare(strict_types=1);

use App\Domain\Identity\IdentityFailure;
use App\Http\Middleware\HandleInertiaRequests;
use App\Http\Middleware\PageResponseHeaders;
use App\Http\Middleware\RedactIdentityCallback;
use App\Http\Middleware\RequestTelemetry;
use App\Http\Middleware\RequireConsoleHost;
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
    ->withMiddleware(function (Middleware $middleware): void {
        $middleware->prepend(RequestTelemetry::class);
        $middleware->web(prepend: [RequireConsoleHost::class], append: [RedactIdentityCallback::class, HandleInertiaRequests::class, PageResponseHeaders::class]);
    })
    ->withExceptions(function (Exceptions $exceptions): void {
        $exceptions->dontReport([IdentityFailure::class]);
        $exceptions->dontFlash(['current_password', 'password', 'password_confirmation', 'client_secret', 'code', 'state']);
        $exceptions->render(function (IdentityFailure $error) {
            return response('Sign-in is temporarily unavailable. Please try again.', $error->status, ['Cache-Control' => 'no-store, private']);
        });
    })
    ->create();
