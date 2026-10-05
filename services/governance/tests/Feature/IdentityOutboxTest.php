<?php

declare(strict_types=1);

use App\Application\Messaging\Actions\PublishGovernanceEvent;
use App\Application\Messaging\Actions\PublishIdentityEvent;
use App\Application\Messaging\Contracts\ConfirmedPublisher;
use App\Domain\Identity\IdentityLedger;
use App\Domain\Messaging\InvalidEvent;
use App\Infrastructure\Messaging\IdentityEventEncoder;
use Illuminate\Support\Carbon;
use Illuminate\Support\Facades\DB;

beforeEach(function (): void {
    initializeIdentityFixture($this);
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

it('delivers an existing bootstrap fact without rewriting its audit or disclosing credentials', function (): void {
    $audit = DB::table('app.identity_audit')->first();
    expect(app(PublishGovernanceEvent::class)->handle())->toBe('idle')
        ->and(app(PublishIdentityEvent::class)->handle())->toBe('published')
        ->and(app(PublishIdentityEvent::class)->handle())->toBe('idle');
    $sent = $this->transport->sent[0];
    $event = json_decode($sent['wire'], true);
    expect($sent['id'])->toBe($audit->id)->and($sent['route'])->toBe('identity.bootstrap.created.v1')
        ->and($event['scope'])->toBe('installation')->and($event['actor_kind'])->toBe('deployment')
        ->and($event['actor_id'])->toBeNull()->and($event['authority_use'])->toBe('notification_only')
        ->and($event)->not->toHaveKey('tenant_id')->and($sent['wire'])->not->toContain($this->temporary)
        ->and(DB::table('app.identity_audit')->first())->toEqual($audit)
        ->and(DB::table('app.identity_outbox')->value('published_at'))->not->toBeNull();
    $canonical = json_encode(['id' => $audit->id, 'event' => $audit->event, 'actor' => $audit->actor, 'occurred_at' => $event['occurred_at']], JSON_UNESCAPED_SLASHES);
    expect($event['audit_sha256'])->toBe(hash('sha256', $canonical));
});

it('preserves identical identity wire bytes across uncertain confirmation and bounded backoff', function (): void {
    $this->transport->fail = true;
    expect(app(PublishIdentityEvent::class)->handle())->toBe('retry')
        ->and(app(PublishIdentityEvent::class)->handle())->toBe('idle');
    $row = DB::table('app.identity_outbox')->first();
    expect($row->attempts)->toBe(1)->and($row->last_error)->toBe('publication_unconfirmed')->and($row->published_at)->toBeNull();
    $this->travel(3)->seconds();
    $this->transport->fail = false;
    expect(app(PublishIdentityEvent::class)->handle())->toBe('published')
        ->and($this->transport->sent[1])->toBe($this->transport->sent[0]);
});

it('replays identity history after database acknowledgement rollback', function (): void {
    DB::beginTransaction();
    expect(app(PublishIdentityEvent::class)->handle())->toBe('published');
    DB::rollBack();
    expect(DB::table('app.identity_outbox')->value('published_at'))->toBeNull()
        ->and(app(PublishIdentityEvent::class)->handle())->toBe('published')
        ->and($this->transport->sent[1])->toBe($this->transport->sent[0]);
});

it('caps retry delay and isolates a malformed event from the remaining installation history', function (): void {
    DB::table('app.identity_outbox')->update(['event' => 'identity.unknown']);
    DB::transaction(fn () => IdentityLedger::record('identity.login.denied', 'unauthenticated'));
    $this->transport->fail = true;
    DB::table('app.identity_outbox')->where('event', 'identity.login.denied')->update(['attempts' => 999999]);
    $this->travelTo(now()->startOfSecond()->addSecond());
    $results = [app(PublishIdentityEvent::class)->handle(), app(PublishIdentityEvent::class)->handle()];
    sort($results);
    expect($results)->toBe(['quarantined', 'retry']);
    $row = DB::table('app.identity_outbox')->where('event', 'identity.login.denied')->first();
    expect($row->attempts)->toBe(1000000)->and($row->last_error)->toBe('publication_unconfirmed')
        ->and(Carbon::parse($row->available_at)->equalTo(now()->addSeconds(300)))->toBeTrue()
        ->and(DB::table('app.identity_outbox')->where('event', 'identity.unknown')->value('published_at'))->toBeNull();
    $this->travel(301)->seconds();
    $this->transport->fail = false;
    expect(app(PublishIdentityEvent::class)->handle())->toBe('published')
        ->and(app(PublishIdentityEvent::class)->handle())->toBe('idle');
});

it('validates identity event types, audit attribution and immutable row agreement', function (string $field, mixed $value): void {
    $row = DB::table('app.identity_outbox')->first();
    if ($field === 'actor' || $field === 'event') {
        DB::table('app.identity_audit')->update([$field => $value]);
        if ($field === 'event') {
            $row->event = $value;
        }
    } else {
        $row->{$field} = $value;
    }
    expect(fn () => (new IdentityEventEncoder)->encode($row))->toThrow(InvalidEvent::class);
})->with([
    ['actor', 'private-external-subject'], ['actor', '550e8400-e29b-41d4-a716-446655440000'],
    ['event', 'identity.unreviewed'], ['occurred_at', '2000-01-01T00:00:00Z'],
    ['occurred_at', null], ['id', '550e8400-e29b-41d4-a716-446655440000'],
]);

it('reports unavailable audit storage without poisoning a pending fact', function (): void {
    DB::statement('ALTER TABLE app.identity_audit RENAME TO missing_identity_audit');
    $this->artisan('identity:publish-outbox --limit=1')->assertExitCode(1)->expectsOutput('outbox_unavailable');
    expect(DB::table('app.identity_outbox')->value('quarantined_at'))->toBeNull();
    DB::statement('ALTER TABLE app.missing_identity_audit RENAME TO identity_audit');
    expect(app(PublishIdentityEvent::class)->handle())->toBe('published');
});

it('continues delivery after federation retirement and session revocation without reading current authority', function (): void {
    $token = changeLocalPassword($this, localLogin($this));
    $this->withHeader('X-Console-Session', $token)->postJson('/identity/logout')->assertOk();
    DB::table('app.bootstrap_administrator')->update(['state' => 'retired', 'password_hash' => null]);
    $this->artisan('identity:publish-outbox --limit=2')->assertExitCode(0);
    expect($this->transport->sent)->toHaveCount(2);
    $this->artisan('identity:publish-outbox --limit=100')->assertExitCode(0);
    expect(DB::table('app.identity_outbox')->whereNull('published_at')->count())->toBe(0);
});

it('denies invalid batch limits and keeps schemata byte-identical', function (): void {
    $this->artisan('identity:publish-outbox --limit=0')->assertExitCode(1);
    $this->artisan('identity:publish-outbox --limit=501')->assertExitCode(1);
    expect(hash_file('sha256', resource_path('contracts/identity-change-v1.json')))
        ->toBe('3e29ad64056f83e5738f09adb241bd9b4faeb00450101d27dba9b25d123946f4');
});

it('encodes every supported identity event using internal attribution only', function (string $event, string $actor): void {
    DB::transaction(fn () => IdentityLedger::record($event, $actor));
    $row = DB::table('app.identity_outbox')->where('event', $event)->orderByDesc('occurred_at')->first();
    $wire = (new IdentityEventEncoder)->encode($row);
    $fact = json_decode($wire, true);
    expect($fact['event_type'])->toBe($event)->and($fact['scope'])->toBe('installation')
        ->and($fact['actor_id'])->toBe(in_array($actor, ['deployment', 'bootstrap-admin', 'unauthenticated'], true) ? null : $actor)
        ->and($wire)->not->toContain($this->temporary)->not->toContain($this->workload);
})->with([
    ['identity.bootstrap.created', 'deployment'], ['identity.login.denied', 'unauthenticated'],
    ['identity.login.succeeded', 'bootstrap-admin'], ['identity.password.denied', 'bootstrap-admin'],
    ['identity.password.changed', 'bootstrap-admin'], ['identity.oidc.settings_saved', 'bootstrap-admin'],
    ['identity.oidc.administrator_verified', '550e8400-e29b-41d4-a716-446655440000'],
    ['identity.oidc.activated', '550e8400-e29b-41d4-a716-446655440000'],
    ['identity.federated.login', '550e8400-e29b-41d4-a716-446655440000'],
    ['identity.session.revoked', '550e8400-e29b-41d4-a716-446655440000'],
    ['identity.delegation.issued', '550e8400-e29b-41d4-a716-446655440000'],
    ['identity.delegation.revoked', '550e8400-e29b-41d4-a716-446655440000'],
]);
