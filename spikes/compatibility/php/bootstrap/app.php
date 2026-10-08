<?php

declare(strict_types=1);

use App\Domain\Compatibility\Exceptions\InvalidSampleTransition;
use App\Http\Middleware\HandleInertiaRequests;
use Illuminate\Foundation\Application;
use Illuminate\Foundation\Configuration\Exceptions;
use Illuminate\Foundation\Configuration\Middleware;
use Illuminate\Http\JsonResponse;

// The disposable spike has no installed application skeleton or Composer scripts.
foreach (['bootstrap/cache', 'storage/framework/views', 'storage/framework/sessions', 'storage/logs'] as $directory) {
    $path = dirname(__DIR__).'/'.$directory;

    if (! is_dir($path)) {
        mkdir($path, 0755, true);
    }
}

return Application::configure(basePath: dirname(__DIR__))
    ->withRouting(web: __DIR__.'/../routes/web.php')
    ->withMiddleware(function (Middleware $middleware): void {
        $middleware->web(append: [HandleInertiaRequests::class]);
        $middleware->redirectGuestsTo('/compatibility');
    })
    ->withExceptions(function (Exceptions $exceptions): void {
        $exceptions->render(function (InvalidSampleTransition $exception): JsonResponse {
            return response()->json(['message' => $exception->getMessage()], 409);
        });
    })
    ->create();
