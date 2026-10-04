<?php

declare(strict_types=1);

use App\Http\Controllers\CompatibilityController;
use App\Http\Controllers\SampleController;
use Illuminate\Support\Facades\Route;

Route::get('/compatibility', [CompatibilityController::class, 'show'])->name('compatibility');
Route::post('/compatibility/validate', [CompatibilityController::class, 'check'])->name('compatibility.validate');

Route::middleware('auth')->group(function (): void {
    Route::get('/samples', [SampleController::class, 'index'])->name('samples.index');
    Route::post('/samples/{sample}/approve', [SampleController::class, 'approve'])->whereNumber('sample');
});
