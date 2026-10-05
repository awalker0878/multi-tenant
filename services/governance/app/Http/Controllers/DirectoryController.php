<?php

declare(strict_types=1);

namespace App\Http\Controllers;

use App\Application\Tenancy\Actions\ReadDirectory;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;

final class DirectoryController
{
    public function __invoke(Request $request, ReadDirectory $read, ?string $tenant = null): JsonResponse
    {
        $input = $request->validate(['cursor' => ['sometimes', 'string', 'min:1', 'max:2048']]);

        return response()->json($read->handle((string) $request->header('X-Console-Session'), $tenant, $input['cursor'] ?? null),
            200, ['Cache-Control' => 'no-store, private']);
    }
}
