<?php

declare(strict_types=1);

use App\Http\Middleware\RequestTelemetry;
use Illuminate\Foundation\Application;
use Illuminate\Foundation\Configuration\Exceptions;
use Illuminate\Foundation\Configuration\Middleware;
use Illuminate\Http\Request;
use Illuminate\Support\Str;
use Illuminate\Validation\ValidationException;
use Symfony\Component\HttpKernel\Exception\HttpExceptionInterface;

return Application::configure(basePath: dirname(__DIR__))
    ->withRouting(using: function (): void {
        require __DIR__.'/../routes/api.php';
    })
    ->withCommands([__DIR__.'/../app/Console/Commands'])
    ->withMiddleware(function (Middleware $middleware): void {
        $middleware->prepend(RequestTelemetry::class);
    })
    ->withExceptions(function (Exceptions $exceptions): void {
        $exceptions->shouldRenderJsonWhen(fn (Request $request, Throwable $exception): bool => true);
        $exceptions->render(function (Throwable $error, Request $request) {
            if (preg_match('#\A(?:/v1/tenants/[0-9a-f-]{36}/(?:migration-qualifications|planning-qualification-v2)|/internal/tenants/[0-9a-f-]{36}/qualification-(?:checks|publications))\z#D', $request->getPathInfo()) !== 1) {
                return null;
            }
            $status = $error instanceof ValidationException ? 422 : ($error instanceof HttpExceptionInterface ? $error->getStatusCode() : 503);
            if (! in_array($status, [401, 403, 404, 409, 413, 422, 423, 503], true)) {
                $status = 503;
            }

            return response()->json(['code' => 'qualification_request_denied',
                'message' => 'Qualification request denied or unavailable', 'correlation_id' => (string) Str::uuid(),
                'retryable' => $status >= 500], $status, ['Cache-Control' => 'no-store, private']);
        });
    })
    ->create();
