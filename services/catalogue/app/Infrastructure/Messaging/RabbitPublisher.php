<?php

declare(strict_types=1);

namespace App\Infrastructure\Messaging;

use PhpAmqpLib\Connection\AMQPConnectionConfig;
use PhpAmqpLib\Connection\AMQPConnectionFactory;
use PhpAmqpLib\Message\AMQPMessage;
use RuntimeException;

final readonly class RabbitPublisher implements ConfirmedPublisher
{
    public function __construct(private string $host, private string $password, private string $ca) {}

    public function publish(string $wire, string $eventId): void
    {
        $config = new AMQPConnectionConfig;
        $config->setHost($this->host);
        $config->setPort(5671);
        $config->setUser('catalogue');
        $config->setPassword($this->password);
        $config->setVhost('product');
        $config->setIsSecure(true);
        $config->setSslCaCert($this->ca);
        $config->setSslVerify(true);
        $config->setSslVerifyName(true);
        $config->setConnectionTimeout(2.0);
        $config->setReadTimeout(5.0);
        $config->setWriteTimeout(5.0);
        $config->setChannelRPCTimeout(5.0);
        $config->setHeartbeat(0);
        $connection = AMQPConnectionFactory::create($config);
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
            $channel->basic_publish(new AMQPMessage($wire, [
                'delivery_mode' => 2,
                'content_type' => 'application/json',
                'message_id' => $eventId,
                'user_id' => 'catalogue',
            ]), 'catalogue.events', 'catalogue.foundation.recorded.v1', true);
            $channel->wait_for_pending_acks_returns(5.0);
            if (! $confirmed || $rejected) {
                throw new RuntimeException('publication_not_confirmed');
            }
        } finally {
            $connection->close();
        }
    }
}
