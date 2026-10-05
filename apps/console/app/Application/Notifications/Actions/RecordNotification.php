<?php

declare(strict_types=1);

namespace App\Application\Notifications\Actions;

use App\Application\Notifications\Contracts\NotificationDecoder;
use App\Application\Notifications\Data\Delivery;
use App\Domain\Notifications\InvalidNotification;
use Illuminate\Support\Facades\Crypt;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Str;
use RuntimeException;

final class RecordNotification
{
    public function __construct(private NotificationDecoder $decoder) {}

    public function handle(Delivery $delivery): string
    {
        // Never acknowledge a truncated body: custody must include every byte.
        if ($delivery->truncated || strlen($delivery->wire) > 16384
            || max(array_map(strlen(...), [$delivery->messageId, $delivery->routingKey, $delivery->publisher, $delivery->contentType])) > 255) {
            throw new RuntimeException('notification_oversized');
        }

        return DB::transaction(function () use ($delivery): string {
            try {
                $event = $this->decoder->decode($delivery);
            } catch (InvalidNotification) {
                return $this->quarantine($delivery, 'invalid_notification');
            }
            $digest = hash('sha256', $delivery->wire);
            $inserted = DB::table('app.notification_inbox')->insertOrIgnore([
                'event_id' => $event->id, 'tenant_id' => $event->tenantId, 'event_type' => $event->type,
                'wire_sha256' => $digest, 'received_at' => now(),
            ]);
            if ($inserted === 0) {
                $original = DB::table('app.notification_inbox')->where('event_id', $event->id)->value('wire_sha256');

                return $original === $digest ? 'duplicate' : $this->quarantine($delivery, 'conflicting_event');
            }
            // This is an opaque invalidation hint, never a resource revision or grant.
            // Reordering can prompt another refresh; it cannot regress owner state.
            DB::table('app.notification_hints')->upsert([
                'tenant_id' => $event->tenantId, 'cursor' => (string) Str::uuid(), 'updated_at' => now(),
            ], ['tenant_id'], ['cursor', 'updated_at']);

            return 'recorded';
        });
    }

    private function quarantine(Delivery $delivery, string $reason): string
    {
        $envelope = serialize([$delivery->wire, $delivery->messageId, $delivery->routingKey, $delivery->publisher, $delivery->contentType]);
        DB::table('app.notification_quarantine')->insertOrIgnore([
            'envelope_sha256' => hash('sha256', $envelope), 'reason' => $reason,
            'envelope_ciphertext' => Crypt::encryptString($envelope), 'received_at' => now(),
        ]);

        return 'quarantined';
    }
}
