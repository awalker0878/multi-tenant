<?php

declare(strict_types=1);

use App\Domain\Identity\IdentityDenied;
use App\Http\Middleware\RequestTelemetry;
use Illuminate\Console\Scheduling\Schedule;
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
    ->withSchedule(function (Schedule $schedule): void {
        // Database claims provide cross-replica exclusion; no cache lock is authority.
        $schedule->command('governance:expire-approvals --limit=100')->everyMinute();
        $schedule->command('governance:publish-outbox --limit=10')->everyMinute();
        $schedule->command('identity:publish-outbox --limit=10')->everyMinute();
        $schedule->command('support:expire-access --limit=100')->everyMinute();
        $schedule->command('support:publish-outbox --limit=10')->everyMinute();
    })
    ->withMiddleware(function (Middleware $middleware): void {
        $middleware->prepend(RequestTelemetry::class);
    })
    ->withExceptions(function (Exceptions $exceptions): void {
        $exceptions->shouldRenderJsonWhen(fn (Request $request, Throwable $exception): bool => true);
        $exceptions->dontReport([IdentityDenied::class]);
        $exceptions->dontFlash(['current_password', 'password', 'password_confirmation', 'client_secret', 'code', 'state', 'browser_binding', 'verification_token', 'delegation_token']);
        $delegationRequest = static fn (Request $request): bool => preg_match(
            '#\\A/v1/tenants/[0-9a-f-]{36}/(?:actor-delegations(?:/[0-9a-f-]{36}/revocation)?|delegated-authorizations)\\z#D',
            $request->getPathInfo()
        ) === 1;
        $errorBody = static fn (string $code, int $status): array => [
            'code' => $code, 'message' => 'Delegation request denied or unavailable',
            'correlation_id' => (string) Str::uuid(), 'retryable' => $status >= 500,
        ];
        $exceptions->render(function (IdentityDenied $error, Request $request) use ($delegationRequest, $errorBody) {
            if ($delegationRequest($request)) {
                return response()->json($errorBody($error->reason, $error->status), $error->status,
                    ['Cache-Control' => 'no-store, private']);
            }

            return response()->json(['error' => $error->reason], $error->status, [
                'Cache-Control' => 'no-store, private',
                ...($error->status === 429 ? ['Retry-After' => (string) config('identity.lock_seconds')] : []),
            ]);
        });
        $exceptions->render(function (ValidationException $error, Request $request) use ($delegationRequest, $errorBody) {
            if ($delegationRequest($request) === false) {
                return null;
            }

            return response()->json($errorBody('delegation_input_invalid', 422), 422,
                ['Cache-Control' => 'no-store, private']);
        });
        $exceptions->render(function (Throwable $error, Request $request) use ($delegationRequest, $errorBody) {
            if ($delegationRequest($request) === false) {
                return null;
            }
            $status = $error instanceof HttpExceptionInterface ? $error->getStatusCode() : 503;
            if (in_array($status, [401, 403, 404, 409, 422, 429, 503], true) === false) {
                $status = 503;
            }

            return response()->json($errorBody('delegation_unavailable', $status), $status,
                ['Cache-Control' => 'no-store, private']);
        });
    })
    ->create();
