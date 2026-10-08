<?php

declare(strict_types=1);

use App\Application\Messaging\Actions\PublishSupportEvent;
use App\Application\Messaging\Contracts\ConfirmedPublisher;
use App\Domain\Messaging\InvalidEvent;
use App\Domain\Support\SupportLedger;
use App\Infrastructure\Messaging\SupportEventEncoder;
use Illuminate\Support\Facades\DB;

beforeEach(function (): void {
    initializeSupportFixture($this);
    DB::table('app.support_outbox')->update(['published_at' => now()]);
    $this->supportRequest = createSupportRequest($this);
    $this->transport = new class implements ConfirmedPublisher
    {
        public array $sent = [];

        public bool $fail = false;

        public function publish(string $wire, string $eventId, string $routingKey): void
        {
            $this->sent[] = ['wire' => $wire, 'id' => $eventId, 'route' => $routingKey];
            if ($this->fail) {
                throw new RuntimeException('private broker credential must not be recorded');
            }
        }
    };
    app()->instance(ConfirmedPublisher::class, $this->transport);
});

afterEach(function (): void {
    unlink($this->credentialFile);
    $this->travelBack();
});

it('publishes only restricted audit references with stable bytes across uncertain delivery', function (): void {
    $audit = DB::table('app.support_audit')->where('event', 'support.access.requested')->first();
    $this->transport->fail = true;
    expect(app(PublishSupportEvent::class)->handle())->toBe('retry')
        ->and(app(PublishSupportEvent::class)->handle())->toBe('idle');
    $row = DB::table('app.support_outbox')->where('id', $audit->id)->first();
    expect($row->last_error)->toBe('publication_unconfirmed')->and($row->published_at)->toBeNull();
    $this->travel(3)->seconds();
    $this->transport->fail = false;
    DB::beginTransaction();
    expect(app(PublishSupportEvent::class)->handle())->toBe('published');
    DB::rollBack();
    expect(app(PublishSupportEvent::class)->handle())->toBe('published')
        ->and($this->transport->sent[1])->toBe($this->transport->sent[0])
        ->and($this->transport->sent[2])->toBe($this->transport->sent[0]);
    $sent = $this->transport->sent[0];
    $event = json_decode($sent['wire'], true);
    expect($sent['id'])->toBe($audit->id)->and($sent['route'])->toBe('support.access.requested.v1')
        ->and($event['tenant_id'])->toBe($this->tenant)->and($event['resource_id'])->toBe($this->supportRequest['id'])
        ->and($event['actor_id'])->toBe($this->requesterId)->and($event['authority_use'])->toBe('notification_only')
        ->and($event)->not->toHaveKeys(['facts', 'binding', 'session_hash', 'case_reference', 'reason_code'])
        ->and($sent['wire'])->not->toContain($this->temporary, $this->requester, 'INC-100', $this->targetMembership['id'])
        ->and(DB::table('app.support_audit')->where('id', $audit->id)->first())->toEqual($audit);
    $canonical = json_encode(['event' => $audit->event, 'occurred_at' => $event['occurred_at'], 'payload' => json_decode($audit->payload_json, true)], JSON_UNESCAPED_SLASHES);
    expect($event['audit_sha256'])->toBe(hash('sha256', $canonical));
});

it('rejects outbox disagreement without losing later immutable facts', function (string $field, mixed $value): void {
    $row = DB::table('app.support_outbox')->where('event', 'support.access.requested')->first();
    $row->{$field} = $value;
    expect(fn () => (new SupportEventEncoder)->encode($row))->toThrow(InvalidEvent::class);
})->with([
    ['event', 'support.access.unreviewed'], ['tenant_id', '550e8400-e29b-41d4-a716-446655440000'],
    ['payload_json', '{}'], ['occurred_at', null], ['occurred_at', '2000-01-01T00:00:00Z'],
]);

it('quarantines malformed facts while storage outage leaves a claim retriable', function (): void {
    DB::statement('ALTER TABLE app.support_audit RENAME TO missing_support_audit');
    $this->artisan('support:publish-outbox --limit=1')->assertExitCode(1)->expectsOutput('outbox_unavailable');
    expect(DB::table('app.support_outbox')->whereNull('published_at')->value('quarantined_at'))->toBeNull();
    DB::statement('ALTER TABLE app.missing_support_audit RENAME TO support_audit');
    DB::table('app.support_outbox')->whereNull('published_at')->update(['event' => 'support.access.unknown']);
    expect(app(PublishSupportEvent::class)->handle())->toBe('quarantined');
    supportDecision($this, $this->supportRequest, 'reject', $this->owner, ['role' => 'tenant', 'case_reference' => 'INC-100', 'reason_code' => 'request_rejected'])->assertOk();
    expect(app(PublishSupportEvent::class)->handle())->toBe('published');
});

it('delivers every declared support fact without depending on current sessions', function (): void {
    $schema = json_decode(file_get_contents(resource_path('contracts/support-change-v1.json')), true);
    foreach ($schema['properties']['event_type']['enum'] as $event) {
        DB::transaction(fn () => SupportLedger::record($this->tenant,
            in_array($event, ['support.access.expired', 'support.access.invalidated'], true) ? null : $this->requesterId,
            $event, $this->supportRequest['id'], 1, ['case_reference' => 'SENSITIVE-REFERENCE']));
    }
    DB::table('app.federated_sessions')->update(['revoked_at' => now()]);
    $this->provider->unavailable = true;
    $this->artisan('support:publish-outbox --limit=100')->assertExitCode(0);
    expect(DB::table('app.support_outbox')->whereNull('published_at')->count())->toBe(0);
    foreach ($this->transport->sent as $sent) {
        expect($sent['wire'])->not->toContain('SENSITIVE-REFERENCE', $this->workload, $this->executor);
    }
});

it('bounds relay and expiry batches without authorizing from scheduler success', function (): void {
    $this->artisan('support:publish-outbox --limit=0')->assertExitCode(1);
    $this->artisan('support:publish-outbox --limit=501')->assertExitCode(1);
    $this->artisan('support:expire-access --limit=0')->assertExitCode(1);
    $this->artisan('support:expire-access --limit=501')->assertExitCode(1);
    $this->travel(11)->minutes();
    $this->artisan('support:expire-access --limit=1')->assertExitCode(0)->expectsOutput('{"expired":1}');
    $this->artisan('support:expire-access --limit=1')->assertExitCode(0)->expectsOutput('{"expired":0}');
    expect(DB::table('app.support_requests')->value('state'))->toBe('expired')
        ->and(DB::table('app.support_audit')->where('event', 'support.access.expired')->count())->toBe(1);
});
