<?php

declare(strict_types=1);

namespace App\Application\Compatibility\Actions;

use App\Domain\Compatibility\Models\Actor;
use App\Domain\Compatibility\Models\Sample;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Gate;

final class ApproveSample
{
    public function handle(Actor $actor, int $sampleId, int $expectedRevision): Sample
    {
        return DB::transaction(function () use ($actor, $sampleId, $expectedRevision): Sample {
            $sample = Sample::query()
                ->where('tenant_id', $actor->tenant_id)
                ->lockForUpdate()
                ->findOrFail($sampleId);

            Gate::forUser($actor)->authorize('approve', $sample);
            $sample->approve($expectedRevision);
            $sample->saveOrFail();

            // Both local writes must roll back when the second write fails.
            DB::table('compatibility_audits')->insert([
                'sample_id' => $sample->id,
                'revision' => $sample->revision,
                'actor_id' => $actor->id,
            ]);

            return $sample;
        });
    }
}
