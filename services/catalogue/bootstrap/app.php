<?php

declare(strict_types=1);

use App\Domain\Authorization\AccessDenied;
use App\Domain\IntentRevisions\IntentFailure;
use App\Http\Middleware\RequestTelemetry;
use App\Http\Middleware\RequireDelegatedActor;
use Illuminate\Database\QueryException;
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
        $exceptions->dontReport([AccessDenied::class, QueryException::class, IntentFailure::class]);
        $exceptions->render(fn (IntentFailure $error) => response()->json(['error' => $error->reason, 'field' => $error->field], $error->status, ['Cache-Control' => 'no-store, private']));
        $exceptions->render(fn (QueryException $error) => response()->json(['error' => in_array($error->getCode(), ['23505', '23503'], true) ? 'reference_or_identity_conflict' : 'persistence_unavailable'], in_array($error->getCode(), ['23505', '23503'], true) ? 409 : 503, ['Cache-Control' => 'no-store, private']));
        $exceptions->render(fn (AccessDenied $error) => response()->json(['error' => 'access_unavailable'], $error->status, ['Cache-Control' => 'no-store, private']));
        $exceptions->shouldRenderJsonWhen(fn (Request $request, Throwable $exception): bool => true);
    })
    ->create();
