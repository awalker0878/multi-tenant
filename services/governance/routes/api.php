<?php

declare(strict_types=1);

use App\Http\Controllers\ApprovalController;
use App\Http\Controllers\CatalogueOwnerController;
use App\Http\Controllers\DelegationController;
use App\Http\Controllers\DependencyHealthController;
use App\Http\Controllers\DirectoryController;
use App\Http\Controllers\HealthController;
use App\Http\Controllers\InventoryCollectionController;
use App\Http\Controllers\LocalIdentityController;
use App\Http\Controllers\OidcController;
use App\Http\Controllers\PlanningInputController;
use App\Http\Controllers\SupportAccessController;
use App\Http\Controllers\TenantController;
use App\Http\Middleware\AuthenticateConsole;
use App\Http\Middleware\AuthenticateService;
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

Route::prefix('v1/tenants')->middleware(AuthenticateConsole::class)->group(function (): void {
    Route::get('/', [TenantController::class, 'index']);
    Route::post('/', [TenantController::class, 'create']);
    Route::get('/{tenant}', [TenantController::class, 'show'])->whereUuid('tenant');
    foreach (['memberships', 'grants', 'quota', 'audit'] as $view) {
        Route::get('/{tenant}/'.$view, [TenantController::class, 'show'])->whereUuid('tenant')->defaults('view', $view);
    }
    foreach (['state' => 'state', 'memberships' => 'membership', 'grants' => 'grant', 'grant-revocations' => 'revoke_grant', 'quota' => 'quota'] as $path => $operation) {
        Route::post('/{tenant}/'.$path, [TenantController::class, 'update'])->whereUuid('tenant')->defaults('operation', $operation);
    }
    Route::post('/{tenant}/authorization-decisions', [TenantController::class, 'decision'])->whereUuid('tenant');
});

Route::get('/v1/tenant-directory', DirectoryController::class)->middleware(AuthenticateConsole::class);
Route::get('/v1/tenants/{tenant}/membership-directory', DirectoryController::class)
    ->whereUuid('tenant')->middleware(AuthenticateConsole::class);

Route::prefix('v1/tenants/{tenant}/approvals')->whereUuid('tenant')->middleware(AuthenticateConsole::class)->group(function (): void {
    Route::post('/', [ApprovalController::class, 'request']);
    Route::get('/{approval}', [ApprovalController::class, 'show'])->whereUuid('approval');
    foreach (['approve', 'reject', 'revoke'] as $operation) {
        Route::post('/{approval}/'.$operation, [ApprovalController::class, 'transition'])->whereUuid('approval')->defaults('operation', $operation);
    }
    Route::post('/{approval}/validations', [ApprovalController::class, 'validateApproval'])->whereUuid('approval');
});

Route::prefix('v1/tenants/{tenant}/actor-delegations')->whereUuid('tenant')->middleware(AuthenticateConsole::class)->group(function (): void {
    Route::post('/', [DelegationController::class, 'issue']);
    Route::post('/{delegation}/revocation', [DelegationController::class, 'revoke'])->whereUuid('delegation');
});
Route::post('/v1/tenants/{tenant}/delegated-authorizations', [DelegationController::class, 'inspect'])
    ->whereUuid('tenant')->middleware(AuthenticateService::class);

Route::middleware(AuthenticateConsole::class)->group(function (): void {
    Route::post('/v1/support-security-grants', [SupportAccessController::class, 'security'])->defaults('operation', 'grant');
    Route::post('/v1/support-security-revocations', [SupportAccessController::class, 'security'])->defaults('operation', 'revoke');
    Route::prefix('/v1/tenants/{tenant}/support-access')->whereUuid('tenant')->group(function (): void {
        Route::post('/', [SupportAccessController::class, 'request']);
        Route::get('/{support}', [SupportAccessController::class, 'show'])->whereUuid('support');
        Route::get('/{support}/audit', [SupportAccessController::class, 'show'])->whereUuid('support')->defaults('history', true);
        foreach (['approve', 'reject', 'revoke', 'review'] as $operation) {
            Route::post('/{support}/'.$operation, [SupportAccessController::class, 'decide'])->whereUuid('support')->defaults('operation', $operation);
        }
        foreach (['activate', 'inspect'] as $operation) {
            Route::post('/{support}/'.$operation, [SupportAccessController::class, 'use'])->whereUuid('support')->defaults('operation', $operation);
        }
    });
});

Route::post('/v1/tenants/{tenant}/catalogue-owner-checks', CatalogueOwnerController::class)->whereUuid('tenant')->middleware(AuthenticateService::class);

Route::post('/v1/tenants/{tenant}/inventory-collection-checks', InventoryCollectionController::class)->whereUuid('tenant')->middleware(AuthenticateService::class);

Route::post('/v1/tenants/{tenant}/planning-input-checks', PlanningInputController::class)->whereUuid('tenant')->middleware(AuthenticateService::class);
