<?php

declare(strict_types=1);

use App\Http\Controllers\DependencyHealthController;
use App\Http\Controllers\HealthController;
use App\Http\Controllers\PlanningQualificationController;
use Illuminate\Support\Facades\Route;

Route::get('/health/live', [HealthController::class, 'live'])->name('health.live');
Route::get('/health/ready', [HealthController::class, 'ready'])->name('health.ready');

Route::get('/health/dependencies', DependencyHealthController::class)->name('health.dependencies');

Route::post('/v1/tenants/{tenant}/planning-qualification', PlanningQualificationController::class)->whereUuid('tenant');
