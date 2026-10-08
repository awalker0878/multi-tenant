<?php

declare(strict_types=1);

use App\Http\Controllers\DependencyHealthController;
use App\Http\Controllers\EvidenceController;
use App\Http\Controllers\HealthController;
use App\Http\Controllers\MigrationQualificationController;
use App\Http\Controllers\PlanningQualificationController;
use App\Http\Controllers\QualificationCurrentController;
use Illuminate\Support\Facades\Route;

Route::get('/health/live', [HealthController::class, 'live'])->name('health.live');
Route::get('/health/ready', [HealthController::class, 'ready'])->name('health.ready');

Route::get('/health/dependencies', DependencyHealthController::class)->name('health.dependencies');

Route::post('/v1/tenants/{tenant}/migration-qualifications', MigrationQualificationController::class)->whereUuid('tenant');

Route::post('/internal/tenants/{tenant}/qualification-checks', QualificationCurrentController::class)->whereUuid('tenant');

Route::post('/v1/tenants/{tenant}/planning-qualification-v2', PlanningQualificationController::class)->whereUuid('tenant');

Route::post('/v1/tenants/{tenant}/planning-qualification', PlanningQualificationController::class)->whereUuid('tenant');

Route::post('/v1/tenants/{tenant}/evidence-uploads', [EvidenceController::class, 'upload'])->whereUuid('tenant');
Route::post('/v1/tenants/{tenant}/evidence-uploads/{evidence}/finalization', [EvidenceController::class, 'finalize'])->whereUuid(['tenant', 'evidence']);
Route::get('/v1/tenants/{tenant}/evidence/{evidence}', [EvidenceController::class, 'show'])->whereUuid(['tenant', 'evidence']);
Route::post('/v1/tenants/{tenant}/evidence/{evidence}/reviews', [EvidenceController::class, 'review'])->whereUuid(['tenant', 'evidence']);
