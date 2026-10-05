<?php

declare(strict_types=1);

namespace App\Infrastructure\Notifications;

use App\Application\Notifications\Contracts\NotificationDecoder;
use App\Application\Notifications\Data\Delivery;
use App\Domain\Notifications\InvalidNotification;
use App\Domain\Notifications\TenantNotification;
use JsonException;
use Opis\JsonSchema\Validator;
use RuntimeException;
use stdClass;

final class GovernanceNotificationDecoder implements NotificationDecoder
{
    private const TYPES = ['governance.tenant.changed', 'governance.membership.changed', 'governance.grant.changed', 'governance.grant.revoked', 'governance.quota.changed'];

    public function decode(Delivery $delivery): TenantNotification
    {
        // A missing/corrupt packaged contract is an operational failure, not poison data.
        $schema = json_decode((string) file_get_contents(resource_path('contracts/governance-change-v1.json')));
        if (! $schema instanceof stdClass) {
            throw new RuntimeException('notification_contract_unavailable');
        }
        try {
            $event = json_decode($delivery->wire, false, 32, JSON_THROW_ON_ERROR);
        } catch (JsonException) {
            throw new InvalidNotification('invalid_notification');
        }
        if (! $event instanceof stdClass || ! (new Validator)->validate($event, $schema)->isValid()
            || ! in_array($event->event_type, self::TYPES, true)
            || $delivery->publisher !== 'governance' || $delivery->contentType !== 'application/json'
            || $delivery->messageId !== $event->event_id || $delivery->routingKey !== $event->event_type.'.v1') {
            throw new InvalidNotification('invalid_notification');
        }

        return new TenantNotification($event->event_id, $event->tenant_id, $event->event_type);
    }
}
