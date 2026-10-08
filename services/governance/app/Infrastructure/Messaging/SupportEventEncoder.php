<?php

declare(strict_types=1);

namespace App\Infrastructure\Messaging;

use App\Application\Messaging\Contracts\EventEncoder;
use App\Domain\Messaging\InvalidEvent;
use Illuminate\Support\Carbon;
use Illuminate\Support\Facades\DB;
use Opis\JsonSchema\Validator;
use stdClass;
use Throwable;

final class SupportEventEncoder implements EventEncoder
{
    public function encode(stdClass $row): string
    {
        // Unavailable storage is retriable, never a malformed committed fact.
        $audit = DB::table('app.support_audit')->where('id', $row->id)->first();
        try {
            if ($audit === null || $audit->event !== $row->event || $audit->tenant_id !== $row->tenant_id
                || ! hash_equals($audit->payload_json, $row->payload_json)
                || ! is_string($row->occurred_at) || ! is_string($audit->occurred_at)
                || ! Carbon::parse($row->occurred_at)->equalTo(Carbon::parse($audit->occurred_at))) {
                throw new InvalidEvent('invalid_event');
            }
            $fact = json_decode($audit->payload_json, true, 32, JSON_THROW_ON_ERROR);
            foreach (['event_id' => $audit->id, 'tenant_id' => $audit->tenant_id, 'actor_id' => $audit->actor_id,
                'resource_id' => $audit->resource_id, 'revision' => $audit->revision, 'correlation_id' => $audit->correlation_id] as $key => $value) {
                if (! array_key_exists($key, $fact) || $fact[$key] !== $value) {
                    throw new InvalidEvent('invalid_event');
                }
            }
            $time = Carbon::parse($audit->occurred_at)->utc()->format('Y-m-d\TH:i:s\Z');
            $canonical = json_encode(['event' => $audit->event, 'occurred_at' => $time, 'payload' => $fact], JSON_THROW_ON_ERROR | JSON_UNESCAPED_SLASHES);
            $event = (object) ['event_type' => $audit->event, 'schema_version' => 1, 'event_id' => $audit->id,
                'tenant_id' => $audit->tenant_id, 'actor_id' => $audit->actor_id, 'resource_id' => $audit->resource_id,
                'revision' => $audit->revision, 'correlation_id' => $audit->correlation_id, 'policy_version' => $fact['policy_version'],
                'audit_sha256' => hash('sha256', $canonical), 'occurred_at' => $time, 'authority_use' => 'notification_only'];
            $schema = json_decode((string) file_get_contents(resource_path('contracts/support-change-v1.json')));
            if (! (new Validator)->validate($event, $schema)->isValid()) {
                throw new InvalidEvent('invalid_event');
            }

            return json_encode($event, JSON_THROW_ON_ERROR | JSON_UNESCAPED_SLASHES);
        } catch (Throwable) {
            throw new InvalidEvent('invalid_event');
        }
    }
}
