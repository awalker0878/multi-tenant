<?php

declare(strict_types=1);

use App\Domain\Notifications\InvalidNotification;
use App\Infrastructure\Notifications\GovernanceNotificationDecoder;
use App\Infrastructure\Notifications\RabbitNotificationSource;

it('accepts the five tenant administration routes without projecting authority', function (string $type): void {
    $delivery = tenantDelivery(['event_type' => $type]);
    $event = (new GovernanceNotificationDecoder)->decode($delivery);
    expect($event->id)->toBe($delivery->messageId)->and($event->type)->toBe($type)
        ->and(get_object_vars($event))->toHaveCount(3);
})->with(['governance.tenant.changed', 'governance.membership.changed', 'governance.grant.changed', 'governance.grant.revoked', 'governance.quota.changed']);

it('rejects unauthorized families, unknown fields, versions and mismatched transport attribution', function (array $event, array $properties): void {
    expect(fn () => (new GovernanceNotificationDecoder)->decode(tenantDelivery($event, $properties)))->toThrow(InvalidNotification::class);
})->with([
    [['event_type' => 'governance.approval.approved'], []],
    [['event_type' => 'identity.session.created'], []],
    [['subject' => 'external-private-subject'], []],
    [['schema_version' => 2], []],
    [['authority_use' => 'permission'], []],
    [['tenant_id' => 'invalid'], []],
    [[], ['publisher' => 'other-service']],
    [[], ['messageId' => '550e8400-e29b-41d4-a716-446655440099']],
    [[], ['routingKey' => 'governance.quota.changed.v2']],
    [[], ['contentType' => 'text/plain']],
    [[], ['wire' => '{bad']],
]);

it('fails before a connection when broker custody is missing', function (): void {
    config(['notifications.host' => null, 'notifications.password_file' => null]);
    expect(fn () => (new RabbitNotificationSource)->next())->toThrow(RuntimeException::class, 'notifications_unavailable');
});
