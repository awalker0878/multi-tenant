<?php

declare(strict_types=1);

namespace App\Http\Controllers;

use App\Application\Evidence\Actions\ManageEvidence;
use App\Application\Evidence\Contracts\EvidenceAuthority;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;

final class EvidenceController
{
    public function upload(Request $request, string $tenant, EvidenceAuthority $authority, ManageEvidence $evidence): JsonResponse
    {
        $authority->producer($request->headers->all());
        abort_if(strlen($request->getContent()) > 100000 || array_diff(array_keys($request->all()), ['job_id', 'plan_digest', 'source_revision', 'digest', 'evidence_level', 'content_base64']) !== [], 422);
        $input = $request->validate(['job_id' => ['required', 'uuid', 'lowercase'], 'plan_digest' => ['required', 'regex:/\A[0-9a-f]{64}\z/'],
            'source_revision' => ['required', 'regex:/\A[0-9a-f]{40}\z/'], 'digest' => ['required', 'regex:/\A[0-9a-f]{64}\z/'],
            'evidence_level' => ['required', 'in:E2'], 'content_base64' => ['required', 'string', 'max:90000']]);

        return response()->json($evidence->upload($tenant, $input), 201)->header('Cache-Control', 'no-store, private');
    }

    public function finalize(Request $request, string $tenant, string $evidence, EvidenceAuthority $authority, ManageEvidence $manager): JsonResponse
    {
        $authority->producer($request->headers->all());
        abort_unless($request->all() === [], 422);

        return response()->json($manager->finalize($tenant, $evidence))->header('Cache-Control', 'no-store, private');
    }

    public function show(Request $request, string $tenant, string $evidence, ManageEvidence $manager): JsonResponse
    {
        return response()->json($manager->read($tenant, $evidence, $request->headers->all()))->header('Cache-Control', 'no-store, private');
    }

    public function review(Request $request, string $tenant, string $evidence, ManageEvidence $manager): JsonResponse
    {
        abort_unless($request->isJson(), 415);
        abort_if(strlen($request->getContent()) > 1024 || array_keys($request->all()) !== ['decision'], 422);
        $input = $request->validate(['decision' => ['required', 'in:accepted_simulation,rejected']]);

        return response()->json($manager->review($tenant, $evidence, $request->headers->all(), $input['decision']), 201)->header('Cache-Control', 'no-store, private');
    }
}
