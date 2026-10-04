<?php

declare(strict_types=1);

use App\Http\Controllers\FoundationController;
use Illuminate\Support\Facades\Route;

Route::get('/', FoundationController::class)->name('foundation');
