<?php

declare(strict_types=1);

use App\Infrastructure\Foundation\ContractResponseBody;
use Psr\Http\Message\StreamInterface;

afterEach(function (): void {
    Mockery::close();
});

it('stops at one byte beyond the configured response limit and closes the stream', function (int $size, bool $oversize): void {
    $read = 0;
    $stream = Mockery::mock(StreamInterface::class);
    $stream->shouldReceive('eof')->andReturnUsing(function () use (&$read, $size): bool {
        return $read >= $size;
    });
    $stream->shouldReceive('read')->andReturnUsing(function (int $length) use (&$read, $size): string {
        $length = min($length, $size - $read);
        $read += $length;

        return str_repeat('a', $length);
    });
    $stream->shouldReceive('close')->once();
    if ($oversize) {
        expect(fn () => ContractResponseBody::read($stream, 310000))->toThrow(LengthException::class);
    } else {
        expect(strlen(ContractResponseBody::read($stream, 310000)))->toBe($size);
    }
    expect($read)->toBe(min($size, 310001));
})->with([[0, false], [310000, false], [310001, true], [5000000, true]]);

it('rejects a stalled stream and closes it', function (): void {
    $stream = Mockery::mock(StreamInterface::class);
    $stream->shouldReceive('eof')->andReturn(false);
    $stream->shouldReceive('read')->once()->andReturn('');
    $stream->shouldReceive('close')->once();
    expect(fn () => ContractResponseBody::read($stream, 310000))->toThrow(UnexpectedValueException::class);
});
