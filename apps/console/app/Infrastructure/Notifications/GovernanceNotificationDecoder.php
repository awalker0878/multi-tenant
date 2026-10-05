<?php

declare(strict_types=1);

namespace App\Infrastructure\Notifications;

use App\Application\Notifications\Contracts\NotificationDecoder;
use App\Application\Notifications\Data\Delivery;
use App\Domain\Notifications\CommittedNotification;
use App\Domain\Notifications\InvalidNotification;
use JsonException;
use Opis\JsonSchema\Validator;
use RuntimeException;
use stdClass;

final class GovernanceNotificationDecoder implements NotificationDecoder
{
    private const TYPES = ['governance.tenant.changed', 'governance.membership.changed', 'governance.grant.changed', 'governance.grant.revoked', 'governance.quota.changed'];

    private const IDENTITY_TYPES = ['identity.bootstrap.created', 'identity.login.denied', 'identity.login.succeeded', 'identity.password.denied', 'identity.password.changed', 'identity.oidc.settings_saved', 'identity.oidc.administrator_verified', 'identity.oidc.activated', 'identity.federated.login', 'identity.session.revoked', 'identity.delegation.issued', 'identity.delegation.revoked'];

    public function decode(Delivery $delivery): CommittedNotification
    {
        // A missing/corrupt packaged contract is an operational failure, not poison data.
        $installation = in_array($delivery->routingKey, array_map(static fn (string $type): string => $type.'.v1', self::IDENTITY_TYPES), true);
        $schema = json_decode((string) file_get_contents(resource_path('contracts/'.($installation ? 'identity-change-v1.json' : 'governance-change-v1.json'))));
        if (! $schema instanceof stdClass) {
            throw new RuntimeException('notification_contract_unavailable');
        }
        try {
            $event = json_decode($delivery->wire, false, 32, JSON_THROW_ON_ERROR);
        } catch (JsonException) {
            throw new InvalidNotification('invalid_notification');
        }
        if (! $event instanceof stdClass || ! (new Validator)->validate($event, $schema)->isValid()
            || ! in_array($event->event_type, $installation ? self::IDENTITY_TYPES : self::TYPES, true)
            || $delivery->publisher !== 'governance' || $delivery->contentType !== 'application/json'
            || $delivery->messageId !== $event->event_id || $delivery->routingKey !== $event->event_type.'.v1') {
            throw new InvalidNotification('invalid_notification');
        }

        return new CommittedNotification($event->event_id, $installation ? null : $event->tenant_id, $event->event_type);
    }
}
