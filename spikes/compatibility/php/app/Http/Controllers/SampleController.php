<?php

declare(strict_types=1);

namespace App\Http\Controllers;

use App\Application\Compatibility\Actions\ApproveSample;
use App\Domain\Compatibility\Models\Actor;
use App\Domain\Compatibility\Models\Sample;
use App\Http\Requests\ApproveSampleRequest;
use App\Http\Resources\SampleResource;
use Illuminate\Http\RedirectResponse;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Gate;
use Inertia\Inertia;
use Inertia\Response;

final class SampleController
{
    public function index(Request $request): Response
    {
        $actor = $request->user();
        abort_unless($actor instanceof Actor, 401);
        Gate::forUser($actor)->authorize('viewAny', Sample::class);

        $samples = Sample::query()->where('tenant_id', $actor->tenant_id)->orderBy('id')->limit(25)->get();

        return Inertia::render('Compatibility', [
            'sampleCount' => $samples->count(),
            'samples' => SampleResource::collection($samples)->resolve($request),
            'notice' => null,
        ]);
    }

    public function approve(ApproveSampleRequest $request, int $sample, ApproveSample $action): RedirectResponse
    {
        $actor = $request->user();
        abort_unless($actor instanceof Actor, 401);

        $action->handle($actor, $sample, $request->integer('expected_revision'));

        return redirect()->route('samples.index');
    }
}
