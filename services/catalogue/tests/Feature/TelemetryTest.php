<?php

declare(strict_types=1);

use App\Application\Foundation\Contracts\SignalBuffer;
use App\Infrastructure\Foundation\BoundedSignalBuffer;

beforeEach(function () {
    $this->signals = sys_get_temp_dir().'/p01-signals-'.bin2hex(random_bytes(8));
    $this->buffer = new BoundedSignalBuffer($this->signals);
    $this->app->instance(SignalBuffer::class, $this->buffer);
    config(['telemetry.enabled' => true, 'telemetry.environment' => 'development', 'telemetry.source_revision' => str_repeat('a', 40)]);
});

afterEach(function () {
    @unlink($this->signals.'/events.jsonl');
    @rmdir($this->signals);
});

test('diagnostic buffer is bounded and stale acknowledgement preserves new records', function () {
    expect($this->buffer->append(['value' => str_repeat('x', 900)]))->toBe('buffered');
    $old = $this->buffer->snapshot();
    $this->buffer->append(['value' => 'later']);
    expect(fn () => $this->buffer->acknowledge(hash('sha256', $old)))->toThrow(RuntimeException::class);
    for ($i = 0; $i < 100; $i++) {
        $state = $this->buffer->append(['value' => str_repeat('x', 900)]);
        if ($state === 'full') {
            break;
        }
    }
    expect($state)->toBe('full');
    $raw = $this->buffer->snapshot();
    expect(strlen($raw))->toBeLessThanOrEqual(BoundedSignalBuffer::LIMIT);
    expect(str_starts_with($raw, $old))->toBeTrue();
    expect($this->buffer->append(['value' => str_repeat('x', 900)]))->toBe('full');
    expect($this->buffer->snapshot())->toBe($raw);
    $this->buffer->acknowledge(hash('sha256', $raw));
    expect($this->buffer->snapshot())->toBe('');
    expect($this->buffer->append(['value' => 'recovered']))->toBe('buffered');
});

test('lock contention and oversized records are explicit without overwriting accepted data', function () {
    $this->buffer->append(['value' => 'first']);
    $handle = fopen($this->signals.'/events.jsonl', 'rb');
    flock($handle, LOCK_EX | LOCK_NB);
    expect($this->buffer->append(['value' => 'contended']))->toBe('contended');
    fclose($handle);
    expect($this->buffer->append(['value' => str_repeat('x', 1024)]))->toBe('unavailable');
    expect($this->buffer->snapshot())->not->toContain('contended');
});

test('unavailable buffer preserves liveness and reports missing collection', function () {
    touch($this->signals);
    try {
        $this->getJson('/health/live')->assertOk()->assertHeader('X-Telemetry-State', 'unavailable');
    } finally {
        unlink($this->signals);
    }
});

test('request signals redact arbitrary inputs and correlate without granting authority', function () {
    $trace = str_repeat('b', 32);
    $parent = str_repeat('c', 16);
    $response = $this->withHeaders([
        'traceparent' => '00-'.$trace.'-'.$parent.'-01',
        'Authorization' => 'Bearer CANARY_PRIVATE', 'Cookie' => 'CANARY_PRIVATE',
        'X-Tenant-Id' => 'CANARY_PRIVATE', 'Baggage' => 'CANARY_PRIVATE',
    ])->getJson('/health/ready?password=CANARY_PRIVATE');
    $response->assertStatus(503)->assertHeader('X-Telemetry-State', 'buffered')->assertHeader('X-Trace-Id', $trace);
    $raw = $this->buffer->snapshot();
    expect($raw)->not->toContain('CANARY_PRIVATE');
    $row = json_decode($raw, true, flags: JSON_THROW_ON_ERROR);
    expect($row['trace_id'])->toBe($trace);
    expect($row['parent_span_id'])->toBe($parent);
    expect($row['span_id'])->toBe($response->headers->get('X-Span-Id'));
    expect($row['status'])->toBe(503);
    expect($row['route'])->toBe('/health/ready');
    expect($row['source_revision'])->toBe(str_repeat('a', 40));
});

test('malformed or zero correlation is replaced and never echoed', function (string $trace) {
    $response = $this->withHeader('traceparent', $trace)->getJson('/health/live')->assertOk();
    $row = json_decode($this->buffer->snapshot(), true, flags: JSON_THROW_ON_ERROR);
    expect($row['parent_span_id'])->toBeNull();
    expect($row['trace_id'])->not->toBe(str_repeat('0', 32));
    expect($row['trace_id'])->toBe($response->headers->get('X-Trace-Id'));
})->with(['malformed', '00-'.str_repeat('0', 32).'-'.str_repeat('c', 16).'-01', '00-'.str_repeat('b', 32).'-'.str_repeat('0', 16).'-01']);
