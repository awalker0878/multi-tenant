<?php

declare(strict_types=1);

namespace App\Http\Controllers;

use App\Application\Foundation\Actions\InspectDependencies;
use App\Application\Foundation\Data\DependencyStatus;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;

final class DependencyHealthController
{
    public function __invoke(Request $request, InspectDependencies $inspect): JsonResponse
    {
        $authorization = $request->header('Authorization');
        $credential = null;
        if (is_string($authorization) && preg_match('/\ABearer ([\x21-\x7e]{32,4096})\z/i', $authorization, $matches)) {
            $credential = $matches[1];
        }
        $status = $inspect->handle($credential);
        $code = match ($status) {
            DependencyStatus::Ready => 200,
            DependencyStatus::Unauthorized => 401,
            DependencyStatus::Unavailable => 503,
        };
        $body = ['service' => 'assurance', 'status' => $status->value, 'scope' => 'foundation_dependencies'];
        $headers = ['Cache-Control' => 'no-store'];
        if ($status === DependencyStatus::Unavailable) {
            $body['reason'] = 'dependency_unavailable';
            $headers['Retry-After'] = '10';
        }
        if ($status === DependencyStatus::Unauthorized) {
            $headers['WWW-Authenticate'] = 'Bearer';
        }

        return new JsonResponse($body, $code, $headers);
    }
}
