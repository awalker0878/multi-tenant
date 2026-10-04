<?php

declare(strict_types=1);

namespace App\Http\Controllers;

use Illuminate\Http\JsonResponse;

final class HealthController
{
    public function live(): JsonResponse
    {
        return new JsonResponse([
            'service' => 'assurance',
            'status' => 'alive',
            'scope' => 'process',
        ], 200, ['Cache-Control' => 'no-store']);
    }

    public function ready(): JsonResponse
    {
        // No environment switch may advertise authority before its checks exist.
        return new JsonResponse([
            'service' => 'assurance',
            'status' => 'not_ready',
            'scope' => 'service',
            'reason' => 'foundation_only',
        ], 503, ['Cache-Control' => 'no-store', 'Retry-After' => '10']);
    }
}
