<?php

declare(strict_types=1);

use App\Http\Controllers\FoundationController;
use App\Http\Controllers\InstallationNotificationController;
use App\Http\Controllers\LocalIdentityController;
use App\Http\Controllers\NotificationController;
use App\Http\Controllers\OidcController;
use App\Http\Controllers\TenantController;
use App\Http\Middleware\RequireIdentity;
use Illuminate\Support\Facades\Route;

Route::get('/', FoundationController::class)->name('foundation');

Route::get('/login', [LocalIdentityController::class, 'login'])->name('identity.login');
Route::post('/login', [LocalIdentityController::class, 'authenticate']);
Route::post('/identity/sign-in', [OidcController::class, 'login']);
Route::get('/identity/callback', [OidcController::class, 'callback']);
Route::middleware(RequireIdentity::class)->group(function (): void {
    Route::get('/password', [LocalIdentityController::class, 'password'])->name('identity.password');
    Route::post('/password', [LocalIdentityController::class, 'updatePassword'])->name('identity.password.update');
    Route::get('/setup', [OidcController::class, 'settings'])->name('identity.setup');
    Route::get('/setup/notification-status', InstallationNotificationController::class);
    Route::put('/setup', [OidcController::class, 'save']);
    Route::post('/setup/test', [OidcController::class, 'test']);
    Route::post('/setup/activate', [OidcController::class, 'activate']);
    Route::get('/account', [TenantController::class, 'index']);
    Route::post('/tenants', [TenantController::class, 'create']);
    Route::get('/tenants/{tenant}', [TenantController::class, 'show'])->whereUuid('tenant');
    Route::get('/tenants/{tenant}/notification-status', NotificationController::class)->whereUuid('tenant');
    Route::post('/tenants/{tenant}/{operation}', [TenantController::class, 'update'])
        ->whereUuid('tenant')->whereIn('operation', ['memberships', 'quota', 'state']);
    Route::post('/logout', [LocalIdentityController::class, 'logout'])->name('identity.logout');
});
