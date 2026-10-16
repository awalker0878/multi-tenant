<?php

declare(strict_types=1);

namespace App\Infrastructure\Foundation;

use LengthException;
use Psr\Http\Message\StreamInterface;
use UnexpectedValueException;

final class ContractResponseBody
{
    public static function read(StreamInterface $stream, int $limit): string
    {
        $raw = '';
        try {
            while (strlen($raw) <= $limit) {
                $chunk = $stream->read(min(65536, $limit + 1 - strlen($raw)));
                $raw .= $chunk;
                if ($stream->eof()) {
                    break;
                }
                if ($chunk === '') {
                    throw new UnexpectedValueException('contract_response_stalled');
                }
            }
            if (strlen($raw) > $limit) {
                throw new LengthException('contract_response_too_large');
            }

            return $raw;
        } finally {
            $stream->close();
        }
    }
}
