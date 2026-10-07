<?php

declare(strict_types=1);

use App\Http\Controllers\CatalogueWorkspaceController;
use App\Http\Controllers\FoundationController;
use App\Http\Controllers\InstallationNotificationController;
use App\Http\Controllers\InventoryController;
use App\Http\Controllers\JobsController;
use App\Http\Controllers\LocalIdentityController;
use App\Http\Controllers\NotificationController;
use App\Http\Controllers\OidcController;
use App\Http\Controllers\PlanningController;
use App\Http\Controllers\PortingConfigurationController;
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

Route::prefix('/tenants/{tenant}')->whereUuid('tenant')->middleware(RequireIdentity::class)->group(function (): void {
    $c = CatalogueWorkspaceController::class;
    Route::get('/applications', [$c, 'index']);
    Route::get('/applications/create', [$c, 'editor']);
    Route::post('/applications', [$c, 'save']);
    Route::get('/applications/{application}', [$c, 'show'])->whereUuid('application');
    Route::get('/applications/{application}/edit', [$c, 'editor'])->whereUuid('application');
    Route::post('/applications/{application}/revisions', [$c, 'save'])->whereUuid('application');
    Route::get('/applications/{application}/status', [$c, 'status'])->whereUuid('application');
    Route::get('/catalogue-references', [$c, 'references']);
    Route::post('/catalogue-references', [$c, 'referenceSave']);
});

Route::prefix('/tenants/{tenant}/inventory')->whereUuid('tenant')->middleware(RequireIdentity::class)->group(function (): void {
    $c = InventoryController::class;
    Route::get('/sites/{site}/configuration', [PortingConfigurationController::class, 'show'])->whereUuid('site');
    Route::get('/sites/{site}/configuration/status', [PortingConfigurationController::class, 'status'])->whereUuid('site');
    Route::post('/sites/{site}/configuration', [PortingConfigurationController::class, 'command'])->whereUuid('site');
    Route::get('/', [$c, 'index']);
    Route::get('/sites/{site}', [$c, 'site'])->whereUuid('site');
    Route::get('/sites/{site}/status', [$c, 'status'])->whereUuid('site');
    Route::get('/sites/{site}/generations/{generation}', [$c, 'resources'])->whereUuid(['site', 'generation']);
    Route::post('/sites/{site}/commands', [$c, 'command'])->whereUuid('site');
});

Route::prefix('/tenants/{tenant}/applications/{application}/environments/{environment}/planning')->whereUuid(['tenant', 'application', 'environment'])->middleware(RequireIdentity::class)->group(function (): void {
    $c = PlanningController::class;
    Route::get('/', [$c, 'index']);
    Route::get('/destinations/{site}', [$c, 'destinations'])->whereUuid('site');
    Route::get('/{kind}/{record}', [$c, 'show'])->whereIn('kind', ['assessments', 'plans'])->whereUuid('record');
    Route::get('/{kind}/{record}/status', [$c, 'status'])->whereIn('kind', ['assessments', 'plans'])->whereUuid('record');
    Route::post('/commands', [$c, 'command']);
});

Route::prefix('/tenants/{tenant}/sites/{site}/applications/{application}/environments/{environment}/jobs')->whereUuid(['tenant', 'site', 'application', 'environment'])->middleware(RequireIdentity::class)->group(function (): void {
    $c = JobsController::class;
    Route::get('/create', [$c, 'create']);
    Route::post('/', [$c, 'admit']);
    Route::get('/{job}', [$c, 'show'])->whereUuid('job');
    Route::get('/{job}/status', [$c, 'status'])->whereUuid('job');
    Route::get('/{job}/evidence/{evidence}/status', [$c, 'evidenceStatus'])->whereUuid(['job', 'evidence']);
    Route::get('/{job}/evidence/{evidence}', [$c, 'evidence'])->whereUuid(['job', 'evidence']);
    Route::post('/{job}/commands', [$c, 'command'])->whereUuid('job');
});
