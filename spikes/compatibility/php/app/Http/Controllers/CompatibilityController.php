<?php

declare(strict_types=1);

namespace App\Http\Controllers;

use App\Http\Requests\CheckCompatibilityRequest;
use Illuminate\Http\RedirectResponse;
use Illuminate\Http\Request;
use Inertia\Inertia;
use Inertia\Response;

final class CompatibilityController
{
    public function show(Request $request): Response
    {
        return Inertia::render('Compatibility', [
            'sampleCount' => 0,
            'notice' => $request->session()->get('notice'),
        ]);
    }

    public function check(CheckCompatibilityRequest $request): RedirectResponse
    {
        $request->validated();

        return redirect()->route('compatibility')->with('notice', 'Compatibility request accepted');
    }
}
