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

final class IdentityEventEncoder implements EventEncoder
{
    public function encode(stdClass $row): string
    {
        // Database failures roll back the claim; they are not invalid history.
        $audit = DB::table('app.identity_audit')->where('id', $row->id)->first();
        try {
            // Read the immutable audit, not the current actor/session/provider.
            if ($audit === null || $audit->event !== $row->event || ! is_string($row->occurred_at)
                || ! is_string($audit->occurred_at) || ! Carbon::parse($row->occurred_at)->equalTo(Carbon::parse($audit->occurred_at))) {
                throw new InvalidEvent('invalid_event');
            }
            $kind = match ($audit->actor) {
                'deployment' => 'deployment', 'bootstrap-admin' => 'bootstrap',
                'unauthenticated' => 'anonymous', default => 'federated',
            };
            $time = Carbon::parse($audit->occurred_at)->utc()->format('Y-m-d\TH:i:s\Z');
            $canonicalAudit = json_encode(['id' => $audit->id, 'event' => $audit->event,
                'actor' => $audit->actor, 'occurred_at' => $time], JSON_THROW_ON_ERROR | JSON_UNESCAPED_SLASHES);
            $event = (object) [
                'event_type' => $row->event, 'schema_version' => 1, 'event_id' => $row->id,
                'scope' => 'installation', 'actor_kind' => $kind,
                'actor_id' => $kind === 'federated' ? $audit->actor : null,
                'audit_sha256' => hash('sha256', $canonicalAudit), 'occurred_at' => $time,
                'authority_use' => 'notification_only',
            ];
            $schema = json_decode((string) file_get_contents(resource_path('contracts/identity-change-v1.json')));
            if (! (new Validator)->validate($event, $schema)->isValid()) {
                throw new InvalidEvent('invalid_event');
            }

            return json_encode($event, JSON_THROW_ON_ERROR | JSON_UNESCAPED_SLASHES);
        } catch (Throwable) {
            throw new InvalidEvent('invalid_event');
        }
    }
}
