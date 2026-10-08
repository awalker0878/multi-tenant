<?php

declare(strict_types=1);

namespace App\Http\Controllers;

use App\Application\Identity\Contracts\IdentityGateway;
use App\Application\Notifications\Contracts\NotificationHints;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Throwable;

final class InstallationNotificationController
{
    public function __invoke(Request $request, IdentityGateway $identity, NotificationHints $hints): JsonResponse
    {
        // The owner checks current installation administration before every hint read.
        $identity->settings((string) $request->session()->get('identity.token'));
        try {
            $cursor = $hints->current('installation');
        } catch (Throwable) {
            return response()->json(['error' => 'notifications_unavailable'], 503, ['Cache-Control' => 'no-store, private']);
        }

        return response()->json(['cursor' => $cursor], 200, ['Cache-Control' => 'no-store, private']);
    }
}
