<?php

declare(strict_types=1);

use App\Application\Messaging\Actions\PublishGovernanceEvent;
use App\Application\Messaging\Contracts\ConfirmedPublisher;
use App\Domain\Messaging\InvalidEvent;
use App\Infrastructure\Messaging\GovernanceEventEncoder;
use App\Infrastructure\Messaging\RabbitPublisher;
use Illuminate\Support\Facades\DB;

beforeEach(function (): void {
    initializeFederationFixture($this);
    $this->tenant = tenantCommand($this, '/v1/tenants', ['name' => 'Private tenant name', 'administrator_subject' => 'immutable-admin-subject'])->assertCreated()->json('id');
    $this->transport = new class implements ConfirmedPublisher
    {
        public array $sent = [];

        public bool $fail = false;

        public function publish(string $wire, string $eventId, string $routingKey): void
        {
            $this->sent[] = ['wire' => $wire, 'id' => $eventId, 'route' => $routingKey];
            if ($this->fail) {
                throw new RuntimeException('synthetic confidential connection failure');
            }
        }
    };
    app()->instance(ConfirmedPublisher::class, $this->transport);
});

afterEach(function (): void {
    unlink($this->credentialFile);
    $this->travelBack();
});

it('publishes a schema-validated minimal fact reference and preserves immutable history', function (): void {
    $row = DB::table('app.governance_outbox')->first();
    expect(app(PublishGovernanceEvent::class)->handle())->toBe('published');
    $event = json_decode($this->transport->sent[0]['wire'], true);
    expect($event['event_id'])->toBe($row->id)
        ->and($event['tenant_id'])->toBe($this->tenant)
        ->and($event['audit_sha256'])->toBe(hash('sha256', $row->payload_json))
        ->and($event['authority_use'])->toBe('notification_only')
        ->and($this->transport->sent[0]['wire'])->not->toContain('Private tenant name')->not->toContain('immutable-admin-subject')
        ->and($this->transport->sent[0]['route'])->toBe('governance.tenant.changed.v1')
        ->and(DB::table('app.governance_outbox')->value('published_at'))->not->toBeNull()
        ->and(DB::table('app.governance_audit')->value('payload_json'))->toBe($row->payload_json)
        ->and(app(PublishGovernanceEvent::class)->handle())->toBe('idle');
});

it('retains an uncertain publication and replays exactly the same event after backoff', function (): void {
    $this->transport->fail = true;
    expect(app(PublishGovernanceEvent::class)->handle())->toBe('retry')
        ->and(app(PublishGovernanceEvent::class)->handle())->toBe('idle');
    $row = DB::table('app.governance_outbox')->first();
    expect($row->published_at)->toBeNull()->and($row->attempts)->toBe(1)->and($row->last_error)->toBe('publication_unconfirmed');
    $this->travel(3)->seconds();
    $this->transport->fail = false;
    expect(app(PublishGovernanceEvent::class)->handle())->toBe('published')
        ->and($this->transport->sent[1])->toBe($this->transport->sent[0]);
});

it('replays a confirmed event after the database acknowledgement is rolled back', function (): void {
    try {
        DB::transaction(function (): void {
            expect(app(PublishGovernanceEvent::class)->handle())->toBe('published');
            throw new RuntimeException('synthetic crash before outer commit');
        });
    } catch (RuntimeException) {
        // Broker accepted, but the database commit did not happen.
    }
    expect(DB::table('app.governance_outbox')->value('published_at'))->toBeNull()
        ->and(app(PublishGovernanceEvent::class)->handle())->toBe('published')
        ->and($this->transport->sent)->toHaveCount(2)
        ->and($this->transport->sent[1])->toBe($this->transport->sent[0]);
});

it('delivers committed history even when its originating actor no longer has authority', function (): void {
    DB::table('app.tenant_memberships')->where('tenant_id', $this->tenant)->update(['state' => 'revoked']);
    DB::table('app.federated_sessions')->update(['revoked_at' => now()]);
    expect(app(PublishGovernanceEvent::class)->handle())->toBe('published');
});

it('quarantines malformed facts without blocking independent tenant events', function (): void {
    DB::table('app.governance_outbox')->update(['payload_json' => '{bad']);
    $other = tenantCommand($this, '/v1/tenants', ['name' => 'Other tenant', 'administrator_subject' => 'immutable-admin-subject'])->assertCreated()->json('id');
    $outcomes = [app(PublishGovernanceEvent::class)->handle(), app(PublishGovernanceEvent::class)->handle()];
    sort($outcomes);
    expect($outcomes)->toBe(['published', 'quarantined'])
        ->and(json_decode($this->transport->sent[0]['wire'], true)['tenant_id'])->toBe($other)
        ->and(DB::table('app.governance_outbox')->whereNotNull('quarantined_at')->count())->toBe(1)
        ->and(DB::table('app.governance_outbox')->where('last_error', 'invalid_event')->value('published_at'))->toBeNull();
});

it('rejects unknown event types and mismatched scope without publishing', function (string $field, string $value): void {
    $row = DB::table('app.governance_outbox')->first();
    $row->{$field} = $value;
    expect(fn () => (new GovernanceEventEncoder)->encode($row))->toThrow(InvalidEvent::class);
})->with([['event', 'governance.allow.all'], ['tenant_id', '550e8400-e29b-41d4-a716-446655440999']]);

it('fails closed without broker custody and bounds operator commands', function (): void {
    app()->instance(ConfirmedPublisher::class, new RabbitPublisher);
    config(['messaging.host' => null]);
    $this->artisan('governance:publish-outbox --limit=1')->assertExitCode(1);
    expect(DB::table('app.governance_outbox')->value('published_at'))->toBeNull();
    $this->artisan('governance:publish-outbox --limit=0')->assertExitCode(1);
    $this->artisan('governance:expire-approvals --limit=501')->assertExitCode(1);
});
