<?php

declare(strict_types=1);

use App\Domain\Authorization\AccessDenied;
use App\Http\Middleware\RequestTelemetry;
use App\Http\Middleware\RequireDelegatedActor;
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
        $middleware->alias(['delegated' => RequireDelegatedActor::class]);
    })
    ->withExceptions(function (Exceptions $exceptions): void {
        $exceptions->dontReport([AccessDenied::class]);
        $exceptions->render(fn (AccessDenied $error) => response()->json(['error' => 'access_unavailable'], $error->status, ['Cache-Control' => 'no-store, private']));
        $exceptions->shouldRenderJsonWhen(fn (Request $request, Throwable $exception): bool => true);
    })
    ->create();
