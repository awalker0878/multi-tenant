<?php

declare(strict_types=1);

namespace App\Infrastructure\Messaging;

use App\Application\Messaging\Contracts\EventEncoder;
use App\Domain\Messaging\InvalidEvent;
use Illuminate\Support\Carbon;
use Opis\JsonSchema\Validator;
use stdClass;
use Throwable;

final class GovernanceEventEncoder implements EventEncoder
{
    public function encode(stdClass $row): string
    {
        try {
            $payload = json_decode($row->payload_json, true, 32, JSON_THROW_ON_ERROR);
            if (! is_array($payload) || ($payload['event_id'] ?? null) !== $row->id || ($payload['tenant_id'] ?? null) !== $row->tenant_id) {
                throw new InvalidEvent('invalid_event');
            }
            // Publish references, never membership subjects, reasons, plan bodies
            // or credentials. Existing committed outbox rows use this same codec.
            $event = (object) [
                'event_type' => $row->event, 'schema_version' => 1, 'event_id' => $row->id,
                'tenant_id' => $row->tenant_id, 'actor_id' => $payload['actor_id'] ?? null,
                'actor_kind' => ($payload['actor_id'] ?? null) === null ? 'system' : 'federated',
                'resource_id' => $payload['resource_id'] ?? null, 'revision' => $payload['revision'] ?? null,
                'audit_sha256' => hash('sha256', $row->payload_json),
                'occurred_at' => Carbon::parse($row->occurred_at)->utc()->format('Y-m-d\TH:i:s\Z'),
                'authority_use' => 'notification_only',
            ];
            $schema = json_decode((string) file_get_contents(resource_path('contracts/governance-change-v1.json')));
            if (! (new Validator)->validate($event, $schema)->isValid()) {
                throw new InvalidEvent('invalid_event');
            }

            return json_encode($event, JSON_THROW_ON_ERROR | JSON_UNESCAPED_SLASHES);
        } catch (Throwable) {
            throw new InvalidEvent('invalid_event');
        }
    }
}
