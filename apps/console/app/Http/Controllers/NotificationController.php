<?php

declare(strict_types=1);

namespace App\Http\Controllers;

use App\Application\Notifications\Contracts\NotificationHints;
use App\Application\Tenancy\Contracts\TenantGateway;
use App\Domain\Identity\IdentityFailure;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Throwable;

final class NotificationController
{
    public function __invoke(Request $request, string $tenant, TenantGateway $tenants, NotificationHints $hints): JsonResponse
    {
        // Current owner authorization precedes every inbox lookup. Browser selectors,
        // cached roles and the notification itself never confer permission.
        $data = $tenants->read((string) $request->session()->get('identity.token'), $tenant);
        if (($data['membership']['role'] ?? null) !== 'tenant_admin'
            || ($data['membership']['site_id'] ?? null) !== null || ($data['membership']['environment'] ?? null) !== null) {
            throw new IdentityFailure(403);
        }
        try {
            $cursor = $hints->current($tenant);
        } catch (Throwable) {
            return response()->json(['error' => 'notifications_unavailable'], 503, ['Cache-Control' => 'no-store, private']);
        }

        return response()->json(['cursor' => $cursor], 200, ['Cache-Control' => 'no-store, private']);
    }
}
