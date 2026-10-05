<?php

declare(strict_types=1);

use App\Http\Controllers\FoundationController;
use App\Http\Controllers\LocalIdentityController;
use App\Http\Middleware\RequireLocalIdentity;
use Illuminate\Support\Facades\Route;

Route::get('/', FoundationController::class)->name('foundation');

Route::get('/login', [LocalIdentityController::class, 'login'])->name('identity.login');
Route::post('/login', [LocalIdentityController::class, 'authenticate']);
Route::middleware(RequireLocalIdentity::class)->group(function (): void {
    Route::get('/password', [LocalIdentityController::class, 'password'])->name('identity.password');
    Route::post('/password', [LocalIdentityController::class, 'updatePassword'])->name('identity.password.update');
    Route::get('/setup', [LocalIdentityController::class, 'setup'])->name('identity.setup');
    Route::post('/logout', [LocalIdentityController::class, 'logout'])->name('identity.logout');
});
