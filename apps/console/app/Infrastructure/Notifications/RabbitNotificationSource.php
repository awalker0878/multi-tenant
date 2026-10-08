<?php

declare(strict_types=1);

namespace App\Infrastructure\Notifications;

use App\Application\Notifications\Contracts\NotificationSource;
use App\Application\Notifications\Data\Delivery;
use App\Infrastructure\Foundation\MountedSecret;
use PhpAmqpLib\Channel\AMQPChannel;
use PhpAmqpLib\Connection\AbstractConnection;
use PhpAmqpLib\Connection\AMQPConnectionConfig;
use PhpAmqpLib\Connection\AMQPConnectionFactory;
use PhpAmqpLib\Message\AMQPMessage;
use RuntimeException;

final class RabbitNotificationSource implements NotificationSource
{
    private ?AbstractConnection $connection = null;

    private ?AMQPChannel $channel = null;

    private ?AMQPMessage $pending = null;

    public function next(): ?Delivery
    {
        if ($this->pending !== null) {
            throw new RuntimeException('notification_ack_pending');
        }
        $this->connect();
        $message = $this->channel?->basic_get('console.governance', false);
        if ($message === null) {
            return null;
        }
        $this->pending = $message;
        $property = static fn (string $name): string => $message->has($name) && is_string($message->get($name)) ? $message->get($name) : '';

        return new Delivery($message->getBody(), $property('message_id'), $message->getRoutingKey() ?? '', $property('user_id'), $property('content_type'), $message->isTruncated());
    }

    public function acknowledge(): void
    {
        if ($this->pending === null) {
            throw new RuntimeException('notification_missing');
        }
        $this->pending->ack();
        $this->pending = null;
    }

    public function close(): void
    {
        try {
            $this->connection?->close();
        } finally {
            $this->pending = null;
            $this->channel = null;
            $this->connection = null;
        }
    }

    private function connect(): void
    {
        if ($this->channel !== null) {
            return;
        }
        $password = (new MountedSecret)->read(config('notifications.password_file'));
        $host = config('notifications.host');
        $ca = config('notifications.ca_file');
        if ($password === null || ! is_string($host) || ! preg_match('/^[a-zA-Z0-9][a-zA-Z0-9.-]{0,252}$/D', $host)
            || ! is_string($ca) || ! str_starts_with($ca, '/') || ! is_readable($ca)) {
            throw new RuntimeException('notifications_unavailable');
        }
        $config = new AMQPConnectionConfig;
        $config->setHost($host);
        $config->setPort((int) config('notifications.port'));
        $config->setUser('console');
        $config->setPassword($password);
        $config->setVhost('product');
        $config->setIsSecure(true);
        $config->setSslCaCert($ca);
        $config->setSslVerify(true);
        $config->setSslVerifyName(true);
        $config->setConnectionTimeout(2.0);
        $config->setReadTimeout(5.0);
        $config->setWriteTimeout(5.0);
        $config->setChannelRPCTimeout(5.0);
        $config->setHeartbeat(0);
        $this->connection = AMQPConnectionFactory::create($config);
        $this->channel = $this->connection->channel();
        $this->channel->setBodySizeLimit(16384);
    }
}
