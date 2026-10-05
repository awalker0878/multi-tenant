<?php

declare(strict_types=1);

use App\Domain\Identity\IdentityDenied;
use App\Http\Middleware\RequestTelemetry;
use Illuminate\Foundation\Application;
use Illuminate\Foundation\Configuration\Exceptions;
use Illuminate\Foundation\Configuration\Middleware;
use Illuminate\Http\Request;

return Application::configure(basePath: dirname(__DIR__))
    ->withRouting(using: function (): void {
        require __DIR__.'/../routes/api.php';
    })
    ->withMiddleware(function (Middleware $middleware): void {
        $middleware->prepend(RequestTelemetry::class);
    })
    ->withExceptions(function (Exceptions $exceptions): void {
        $exceptions->shouldRenderJsonWhen(fn (Request $request, Throwable $exception): bool => true);
        $exceptions->dontReport([IdentityDenied::class]);
        $exceptions->dontFlash(['current_password', 'password', 'password_confirmation']);
        $exceptions->render(function (IdentityDenied $error) {
            return response()->json(['error' => $error->reason], $error->status, [
                'Cache-Control' => 'no-store, private',
                ...($error->status === 429 ? ['Retry-After' => (string) config('identity.lock_seconds')] : []),
            ]);
        });
    })
    ->create();
