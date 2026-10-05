<?php

declare(strict_types=1);

use App\Application\Notifications\Actions\ConsumeNotification;
use App\Application\Notifications\Actions\RecordNotification;
use App\Application\Notifications\Contracts\NotificationSource;
use App\Application\Notifications\Data\Delivery;
use App\Infrastructure\Notifications\RabbitNotificationSource;
use Illuminate\Support\Facades\DB;
use PhpAmqpLib\Connection\AbstractConnection;
use PhpAmqpLib\Connection\AMQPConnectionConfig;
use PhpAmqpLib\Connection\AMQPConnectionFactory;
use PhpAmqpLib\Exception\AMQPProtocolChannelException;
use PhpAmqpLib\Message\AMQPMessage;

function notificationBrokerConnection(string $user = 'console', ?string $ca = null): AbstractConnection
{
    $configuration = new AMQPConnectionConfig;
    $configuration->setHost('127.0.0.1');
    $configuration->setPort((int) config('notifications.port'));
    $configuration->setUser($user);
    $configuration->setPassword(trim(file_get_contents($user === 'console' ? config('notifications.password_file') : getenv('P02_TEST_PUBLISHER_PASSWORD_FILE'))));
    $configuration->setVhost('product');
    $configuration->setIsSecure(true);
    $configuration->setSslCaCert($ca ?? config('notifications.ca_file'));
    $configuration->setSslVerify(true);
    $configuration->setSslVerifyName(true);
    $configuration->setConnectionTimeout(2.0);
    $configuration->setReadTimeout(5.0);
    $configuration->setWriteTimeout(5.0);
    $configuration->setHeartbeat(0);

    return AMQPConnectionFactory::create($configuration);
}

function publishTenantNotification(Delivery $delivery): void
{
    $connection = notificationBrokerConnection('governance');
    try {
        $channel = $connection->channel();
        $confirmed = false;
        $rejected = false;
        $channel->set_ack_handler(static function () use (&$confirmed): void {
            $confirmed = true;
        });
        $reject = static function () use (&$rejected): void {
            $rejected = true;
        };
        $channel->set_nack_handler($reject);
        $channel->set_return_listener($reject);
        $channel->confirm_select();
        $channel->basic_publish(new AMQPMessage($delivery->wire, ['delivery_mode' => 2, 'content_type' => $delivery->contentType,
            'message_id' => $delivery->messageId, 'user_id' => $delivery->publisher]), 'governance.events', $delivery->routingKey, true);
        $channel->wait_for_pending_acks_returns(5.0);
        expect($confirmed)->toBeTrue()->and($rejected)->toBeFalse();
    } finally {
        $connection->close();
    }
}

beforeEach(function (): void {
    if (getenv('P02_TEST_BROKER') !== '1') {
        $this->markTestSkipped('Requires the isolated verified-TLS broker campaign.');
    }
    initializeNotificationFixture();
    $connection = notificationBrokerConnection();
    try {
        $channel = $connection->channel();
        while (($message = $channel->basic_get('console.governance', false)) !== null) {
            $message->ack();
        }
    } finally {
        $connection->close();
    }
});

afterEach(function (): void {
    if (getenv('P02_TEST_BROKER') === '1') {
        app(NotificationSource::class)->close();
    }
});

it('consumes verified TLS messages into PostgreSQL and handles duplicate and conflicting redeliveries', function (): void {
    $delivery = tenantDelivery();
    publishTenantNotification($delivery);
    expect(app(ConsumeNotification::class)->handle())->toBe('recorded');
    $cursor = DB::table('app.notification_hints')->value('cursor');
    publishTenantNotification($delivery);
    expect(app(ConsumeNotification::class)->handle())->toBe('duplicate');
    publishTenantNotification(tenantDelivery(['event_id' => $delivery->messageId, 'revision' => 3]));
    expect(app(ConsumeNotification::class)->handle())->toBe('quarantined')
        ->and(DB::table('app.notification_hints')->value('cursor'))->toBe($cursor)
        ->and(DB::table('app.notification_inbox')->count())->toBe(1)
        ->and(DB::table('app.notification_quarantine')->count())->toBe(1)
        ->and(app(ConsumeNotification::class)->handle())->toBe('idle');
});

it('redelivers the same bytes after the consumer closes between commit and acknowledgement', function (): void {
    $delivery = tenantDelivery();
    publishTenantNotification($delivery);
    $source = app(NotificationSource::class);
    $received = $source->next();
    expect($received->wire)->toBe($delivery->wire)->and(app(RecordNotification::class)->handle($received))->toBe('recorded');
    $source->close();
    expect(app(ConsumeNotification::class)->handle())->toBe('duplicate')
        ->and(DB::table('app.notification_inbox')->count())->toBe(1);
});

it('retains oversized bytes at the broker instead of acknowledging a truncated quarantine', function (): void {
    $delivery = tenantDelivery([], ['wire' => str_repeat('x', 16385)]);
    publishTenantNotification($delivery);
    expect(fn () => app(ConsumeNotification::class)->handle())->toThrow(RuntimeException::class, 'notification_oversized');
    app(NotificationSource::class)->close();
    $connection = notificationBrokerConnection();
    try {
        $received = $connection->channel()->basic_get('console.governance', false);
        expect($received->getBody())->toBe($delivery->wire)->and(DB::table('app.notification_quarantine')->count())->toBe(0);
        $received->ack();
    } finally {
        $connection->close();
    }
});

it('rejects an untrusted broker certificate', function (): void {
    config(['notifications.ca_file' => getenv('P02_UNTRUSTED_CA_FILE')]);
    expect(fn () => (new RabbitNotificationSource)->next())->toThrow(Exception::class);
});

it('does not grant Console queue configuration or reads of another service queue', function (string $operation): void {
    $connection = notificationBrokerConnection();
    try {
        $channel = $connection->channel();
        expect(fn () => $operation === 'configure' ? $channel->queue_declare('console.extra') : $channel->basic_get('p02.private', false))
            ->toThrow(AMQPProtocolChannelException::class, 'ACCESS_REFUSED');
    } finally {
        $connection->close();
    }
})->with(['configure', 'read']);

it('delivers installation settings through the same verified broker without a tenant hint', function (): void {
    $delivery = installationDelivery();
    publishTenantNotification($delivery);
    expect(app(ConsumeNotification::class)->handle())->toBe('recorded')
        ->and(DB::table('app.notification_inbox')->whereNull('tenant_id')->count())->toBe(1)
        ->and(DB::table('app.notification_hints')->count())->toBe(0)
        ->and(DB::table('app.installation_notification_hint')->count())->toBe(1);
    publishTenantNotification($delivery);
    expect(app(ConsumeNotification::class)->handle())->toBe('duplicate');
});
