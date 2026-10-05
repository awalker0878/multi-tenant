<?php

declare(strict_types=1);

use App\Application\Notifications\Actions\ConsumeNotification;
use App\Application\Notifications\Actions\RecordNotification;
use App\Application\Notifications\Contracts\NotificationSource;
use App\Application\Notifications\Data\Delivery;
use App\Infrastructure\Notifications\PostgresNotificationHints;
use Illuminate\Database\QueryException;
use Illuminate\Support\Facades\Crypt;
use Illuminate\Support\Facades\DB;

beforeEach(function (): void {
    initializeNotificationFixture();
    $this->delivery = tenantDelivery();
    $this->source = new class($this->delivery) implements NotificationSource
    {
        public int $acks = 0;

        public bool $failAck = false;

        public bool $closed = false;

        public function __construct(public ?Delivery $delivery) {}

        public function next(): ?Delivery
        {
            return $this->delivery;
        }

        public function acknowledge(): void
        {
            expect(DB::transactionLevel())->toBe(0);
            if ($this->failAck) {
                throw new RuntimeException('synthetic confidential broker details');
            }
            $this->acks++;
        }

        public function close(): void
        {
            $this->closed = true;
        }
    };
    app()->instance(NotificationSource::class, $this->source);
});

it('commits minimal immutable receipts and hints before acknowledgement and deduplicates replay', function (): void {
    $consume = app(ConsumeNotification::class);
    expect($consume->handle())->toBe('recorded');
    $original = DB::table('app.notification_inbox')->first();
    $cursor = app(PostgresNotificationHints::class)->current('550e8400-e29b-41d4-a716-446655440001');
    expect($original->event_id)->toBe($this->delivery->messageId)->and($original->wire_sha256)->toBe(hash('sha256', $this->delivery->wire))
        ->and($cursor)->not->toBeNull()->and($this->source->acks)->toBe(1)
        ->and($consume->handle())->toBe('duplicate')->and($this->source->acks)->toBe(2)
        ->and(DB::table('app.notification_inbox')->first())->toEqual($original)
        ->and(app(PostgresNotificationHints::class)->current($original->tenant_id))->toBe($cursor);
});

it('recovers a commit followed by an uncertain broker acknowledgement without repeating the hint', function (): void {
    $this->source->failAck = true;
    expect(fn () => app(ConsumeNotification::class)->handle())->toThrow(RuntimeException::class);
    $cursor = DB::table('app.notification_hints')->value('cursor');
    $this->source->failAck = false;
    expect(app(ConsumeNotification::class)->handle())->toBe('duplicate')
        ->and(DB::table('app.notification_inbox')->count())->toBe(1)
        ->and(DB::table('app.notification_hints')->value('cursor'))->toBe($cursor);
});

it('rolls back the receipt and leaves delivery unacknowledged when the hint write fails', function (): void {
    DB::statement('DROP TABLE app.notification_hints');
    expect(fn () => app(ConsumeNotification::class)->handle())->toThrow(QueryException::class)
        ->and(DB::table('app.notification_inbox')->count())->toBe(0)->and($this->source->acks)->toBe(0);
});

it('refuses to acknowledge inside an outer transaction', function (): void {
    DB::beginTransaction();
    try {
        expect(fn () => app(ConsumeNotification::class)->handle())->toThrow(RuntimeException::class, 'notification_transaction_active')
            ->and($this->source->acks)->toBe(0);
    } finally {
        DB::rollBack();
    }
});

it('quarantines conflicting bytes without replacing a receipt or another tenant hint', function (): void {
    $record = app(RecordNotification::class);
    $record->handle($this->delivery);
    $original = DB::table('app.notification_inbox')->first();
    $cursor = DB::table('app.notification_hints')->value('cursor');
    $conflict = tenantDelivery(['event_id' => $this->delivery->messageId, 'tenant_id' => '550e8400-e29b-41d4-a716-446655440099']);
    expect($record->handle($conflict))->toBe('quarantined')->and($record->handle($conflict))->toBe('quarantined')
        ->and(DB::table('app.notification_quarantine')->count())->toBe(1)
        ->and(DB::table('app.notification_quarantine')->value('reason'))->toBe('conflicting_event')
        ->and(DB::table('app.notification_inbox')->first())->toEqual($original)
        ->and(DB::table('app.notification_hints')->count())->toBe(1)
        ->and(DB::table('app.notification_hints')->value('cursor'))->toBe($cursor);
});

it('stores bounded poison envelopes encrypted and acknowledges only after quarantine commits', function (): void {
    $this->source->delivery = tenantDelivery([], ['wire' => "invalid private bytes\xff"]);
    expect(app(ConsumeNotification::class)->handle())->toBe('quarantined')->and($this->source->acks)->toBe(1)
        ->and(DB::table('app.notification_hints')->count())->toBe(0);
    $ciphertext = DB::table('app.notification_quarantine')->value('envelope_ciphertext');
    expect($ciphertext)->not->toContain('private bytes')
        ->and(Crypt::decryptString($ciphertext))->toContain("invalid private bytes\xff");
    DB::statement('DROP TABLE app.notification_quarantine');
    expect(fn () => app(ConsumeNotification::class)->handle())->toThrow(QueryException::class)->and($this->source->acks)->toBe(1);
});

it('never acknowledges truncated or oversized payloads', function (array $properties): void {
    $this->source->delivery = tenantDelivery([], $properties);
    expect(fn () => app(ConsumeNotification::class)->handle())->toThrow(RuntimeException::class, 'notification_oversized')
        ->and($this->source->acks)->toBe(0)->and(DB::table('app.notification_quarantine')->count())->toBe(0);
})->with([[['truncated' => true]], [['wire' => str_repeat('x', 16385)]], [['messageId' => str_repeat('x', 256)]]]);

it('keeps reordered events as generic hints and isolates tenants', function (): void {
    $record = app(RecordNotification::class);
    $record->handle(tenantDelivery(['revision' => 10]));
    $cursor = DB::table('app.notification_hints')->value('cursor');
    $record->handle(tenantDelivery(['revision' => 1]));
    $next = DB::table('app.notification_hints')->value('cursor');
    $record->handle(tenantDelivery(['tenant_id' => '550e8400-e29b-41d4-a716-446655440099']));
    expect($next)->not->toBe($cursor)->and(DB::table('app.notification_inbox')->count())->toBe(3)
        ->and(DB::table('app.notification_hints')->count())->toBe(2)
        ->and(app(PostgresNotificationHints::class)->current('550e8400-e29b-41d4-a716-446655440001'))->toBe($next);
});

it('bounds command work and redacts operational errors while closing its source', function (): void {
    $this->artisan('console:consume-notifications --limit=501')->assertExitCode(1);
    expect($this->source->acks)->toBe(0);
    $this->artisan('console:consume-notifications --limit=2')->expectsOutput('{"recorded":1,"duplicate":1,"quarantined":0}')->assertSuccessful();
    expect($this->source->closed)->toBeTrue()->and($this->source->acks)->toBe(2);
    $this->source->failAck = true;
    $this->artisan('console:consume-notifications --limit=1')
        ->expectsOutput('Notification delivery unavailable; unacknowledged messages remain with the broker.')
        ->doesntExpectOutput('synthetic confidential broker details')->assertExitCode(1);
});
