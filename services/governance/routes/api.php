<?php

declare(strict_types=1);

use App\Http\Controllers\DependencyHealthController;
use App\Http\Controllers\HealthController;
use App\Http\Controllers\LocalIdentityController;
use App\Http\Controllers\OidcController;
use App\Http\Middleware\AuthenticateConsole;
use App\Http\Middleware\RequireIdentitySetup;
use Illuminate\Support\Facades\Route;

Route::get('/health/live', [HealthController::class, 'live'])->name('health.live');
Route::get('/health/ready', [HealthController::class, 'ready'])->name('health.ready');

Route::get('/health/dependencies', DependencyHealthController::class)->name('health.dependencies');

Route::prefix('identity')->middleware(AuthenticateConsole::class)->group(function (): void {
    Route::post('/local-sessions', [LocalIdentityController::class, 'login']);
    Route::get('/session', [LocalIdentityController::class, 'session']);
    Route::post('/password', [LocalIdentityController::class, 'password']);
    Route::post('/logout', [LocalIdentityController::class, 'logout']);
    Route::get('/setup', [LocalIdentityController::class, 'setup'])->middleware(RequireIdentitySetup::class);
    Route::get('/oidc', [OidcController::class, 'settings']);
    Route::put('/oidc', [OidcController::class, 'save'])->middleware(RequireIdentitySetup::class);
    Route::post('/oidc/flows', [OidcController::class, 'begin']);
    Route::post('/oidc/callback', [OidcController::class, 'callback']);
    Route::post('/oidc/activation', [OidcController::class, 'activate'])->middleware(RequireIdentitySetup::class);
});
