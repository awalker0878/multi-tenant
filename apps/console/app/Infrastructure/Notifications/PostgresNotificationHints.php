<?php

declare(strict_types=1);

namespace App\Infrastructure\Notifications;

use App\Application\Notifications\Contracts\NotificationHints;
use Illuminate\Support\Facades\DB;

final class PostgresNotificationHints implements NotificationHints
{
    public function current(string $tenant): ?string
    {
        $cursor = $tenant === 'installation'
            ? DB::table('app.installation_notification_hint')->where('id', 1)->value('cursor')
            : DB::table('app.notification_hints')->where('tenant_id', $tenant)->value('cursor');

        return is_string($cursor) ? $cursor : null;
    }
}
