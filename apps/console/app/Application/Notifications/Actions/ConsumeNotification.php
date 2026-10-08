<?php

declare(strict_types=1);

namespace App\Application\Notifications\Actions;

use App\Application\Notifications\Contracts\NotificationSource;
use Illuminate\Support\Facades\DB;
use RuntimeException;

final class ConsumeNotification
{
    public function __construct(private NotificationSource $source, private RecordNotification $record) {}

    public function handle(): string
    {
        // A caller's outer transaction must never defer commit until after the ack.
        if (DB::transactionLevel() !== 0) {
            throw new RuntimeException('notification_transaction_active');
        }
        $delivery = $this->source->next();
        if ($delivery === null) {
            return 'idle';
        }
        $result = $this->record->handle($delivery);
        $this->source->acknowledge();

        return $result;
    }
}
