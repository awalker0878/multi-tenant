<?php

declare(strict_types=1);

use App\Http\Controllers\FoundationController;
use App\Http\Controllers\LocalIdentityController;
use App\Http\Controllers\OidcController;
use App\Http\Middleware\RequireIdentity;
use Illuminate\Support\Facades\Route;
use Inertia\Inertia;

Route::get('/', FoundationController::class)->name('foundation');

Route::get('/login', [LocalIdentityController::class, 'login'])->name('identity.login');
Route::post('/login', [LocalIdentityController::class, 'authenticate']);
Route::post('/identity/sign-in', [OidcController::class, 'login']);
Route::get('/identity/callback', [OidcController::class, 'callback']);
Route::middleware(RequireIdentity::class)->group(function (): void {
    Route::get('/password', [LocalIdentityController::class, 'password'])->name('identity.password');
    Route::post('/password', [LocalIdentityController::class, 'updatePassword'])->name('identity.password.update');
    Route::get('/setup', [OidcController::class, 'settings'])->name('identity.setup');
    Route::put('/setup', [OidcController::class, 'save']);
    Route::post('/setup/test', [OidcController::class, 'test']);
    Route::post('/setup/activate', [OidcController::class, 'activate']);
    Route::get('/account', fn () => Inertia::render('identity/Account'));
    Route::post('/logout', [LocalIdentityController::class, 'logout'])->name('identity.logout');
});
