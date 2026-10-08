<?php

declare(strict_types=1);

namespace App\Http\Controllers;

use App\Application\Foundation\Contracts\SecretReader;
use App\Application\Qualification\Actions\ResolveQualification;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;

/** Service-only revalidation; this route cannot publish or review support. */
final class QualificationCurrentController
{
    public function __invoke(Request $request, string $tenant, SecretReader $secrets, ResolveQualification $resolver): JsonResponse
    {
        $incoming = $secrets->read(config('planning.credential_file'));
        $outgoing = $secrets->read(config('planning.governance_credential_file'));
        abort_if($incoming === null || $outgoing === null || $incoming === $outgoing, 503);
        $values = $request->headers->all('authorization');
        abort_unless(count($values) === 1 && is_string($values[0]) && hash_equals('Bearer '.$incoming, $values[0]), 403);
        abort_if(strlen($request->getContent()) > 32768 || array_keys($request->all()) !== ['qualification_scope'], 422);
        $input = $request->validate(['qualification_scope' => ['required', 'array:tenant_id,site_id,endpoint_id,native_scope,installed_tuple,action,method,profile_digest,artifacts']]);
        abort_unless(($input['qualification_scope']['tenant_id'] ?? null) === $tenant, 403);

        return response()->json($resolver->handle($input['qualification_scope']))->header('Cache-Control', 'no-store, private');
    }
}
