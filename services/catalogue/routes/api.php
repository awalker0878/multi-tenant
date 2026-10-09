<?php

declare(strict_types=1);

use App\Http\Controllers\CatalogueController;
use App\Http\Controllers\CurrentPlanningIntentController;
use App\Http\Controllers\DependencyHealthController;
use App\Http\Controllers\HealthController;
use App\Http\Controllers\PlanningInputController;
use Illuminate\Support\Facades\Route;

Route::get('/health/live', [HealthController::class, 'live'])->name('health.live');
Route::get('/health/ready', [HealthController::class, 'ready'])->name('health.ready');

Route::get('/health/dependencies', DependencyHealthController::class)->name('health.dependencies');

Route::prefix('/v1/tenants/{tenant}')->whereUuid('tenant')->group(function (): void {
    $controller = CatalogueController::class;
    Route::get('/applications', [$controller, 'applications'])->middleware('delegated:application.read');
    Route::post('/applications', [$controller, 'publish'])->middleware('delegated:application.write');
    Route::get('/applications/{application}', [$controller, 'show'])->whereUuid('application')->middleware('delegated:application.read');
    Route::get('/applications/{application}/intent-revisions', [$controller, 'revisions'])->whereUuid('application')->middleware('delegated:application.read');
    Route::post('/applications/{application}/intent-revisions', [$controller, 'publish'])->whereUuid('application')->middleware('delegated:application.write');
    Route::get('/applications/{application}/intent-revisions/{revision}', [$controller, 'revision'])->whereUuid(['application', 'revision'])->middleware('delegated:application.read');
    foreach (['environments' => 'environment', 'wsds' => 'wsd', 'security-domains' => 'security-domain'] as $path => $kind) {
        Route::get('/'.$path, [$controller, 'references'])->defaults('kind', $kind)->middleware('delegated:reference.read');
        Route::post('/'.$path, [$controller, 'referenceWrite'])->defaults('kind', $kind)->middleware('delegated:reference.write');
        Route::put('/'.$path.'/{reference}', [$controller, 'referenceWrite'])->whereUuid('reference')->defaults('kind', $kind)->middleware('delegated:reference.write');
        Route::post('/'.$path.'/{reference}/retirement', [$controller, 'referenceWrite'])->whereUuid('reference')->defaults('kind', $kind)->defaults('retire', 'yes')->middleware('delegated:reference.write');
    }
});

Route::get('/v1/tenants/{tenant}/planning-inputs/{application}/{environment}/{site}/{revision}', PlanningInputController::class)->whereUuid(['tenant', 'application', 'environment', 'site', 'revision']);

Route::get('/internal/tenants/{tenant}/applications/{application}/environments/{environment}/current-planning-intent', CurrentPlanningIntentController::class)->whereUuid(['tenant', 'application', 'environment']);
