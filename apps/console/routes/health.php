<?php

declare(strict_types=1);

use App\Http\Controllers\DependencyHealthController;
use App\Http\Controllers\HealthController;
use Illuminate\Support\Facades\Route;

// Process probes do not start a browser session or disclose dependency details.
Route::get('/health/live', [HealthController::class, 'live'])->name('health.live');
Route::get('/health/ready', [HealthController::class, 'ready'])->name('health.ready');

Route::get('/health/dependencies', DependencyHealthController::class)->name('health.dependencies');
