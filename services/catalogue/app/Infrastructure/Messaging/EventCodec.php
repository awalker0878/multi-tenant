<?php

declare(strict_types=1);

namespace App\Infrastructure\Messaging;

use InvalidArgumentException;
use Opis\JsonSchema\Validator;
use stdClass;

final class EventCodec
{
    public function decode(string $wire): GeneratedEvent
    {
        if (strlen($wire) > 4096) {
            throw new InvalidArgumentException('invalid_event');
        }
        $value = json_decode($wire, flags: JSON_THROW_ON_ERROR);
        $schema = json_decode((string) file_get_contents(__DIR__.'/../../../resources/contracts/foundation-event.json'));
        if (! $value instanceof stdClass || ! (new Validator)->validate($value, $schema)->isValid()) {
            throw new InvalidArgumentException('invalid_event');
        }
        // The schema proves this numeric value is exactly one before typed decoding.
        $value->schema_version = (int) $value->schema_version;

        return new GeneratedEvent(...get_object_vars($value));
    }

    public function canonical(GeneratedEvent $event): string
    {
        $fields = get_object_vars($event);
        ksort($fields, SORT_STRING);

        return json_encode($fields, JSON_THROW_ON_ERROR | JSON_UNESCAPED_SLASHES);
    }
}
