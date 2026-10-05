<?php

declare(strict_types=1);

namespace App\Infrastructure\Messaging;

use App\Application\Messaging\Contracts\ConfirmedPublisher;
use App\Infrastructure\Foundation\MountedSecret;
use PhpAmqpLib\Connection\AMQPConnectionConfig;
use PhpAmqpLib\Connection\AMQPConnectionFactory;
use PhpAmqpLib\Message\AMQPMessage;
use RuntimeException;

final class RabbitPublisher implements ConfirmedPublisher
{
    public function publish(string $wire, string $eventId, string $routingKey): void
    {
        $password = (new MountedSecret)->read(config('messaging.password_file'));
        $host = config('messaging.host');
        $ca = config('messaging.ca_file');
        if ($password === null || ! is_string($host) || ! preg_match('/^[a-zA-Z0-9][a-zA-Z0-9.-]{0,252}$/D', $host)
            || ! is_string($ca) || ! str_starts_with($ca, '/') || ! is_readable($ca)) {
            throw new RuntimeException('messaging_unavailable');
        }
        $config = new AMQPConnectionConfig;
        $config->setHost($host);
        $config->setPort((int) config('messaging.port'));
        $config->setUser('governance');
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
                'delivery_mode' => 2, 'content_type' => 'application/json',
                'message_id' => $eventId, 'user_id' => 'governance',
            ]), 'governance.events', $routingKey, true);
            $channel->wait_for_pending_acks_returns(5.0);
            if (! $confirmed || $rejected) {
                throw new RuntimeException('publication_unconfirmed');
            }
        } finally {
            $connection->close();
        }
    }
}
