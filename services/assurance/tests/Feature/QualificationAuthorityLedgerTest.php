<?php

declare(strict_types=1);

use App\Application\Qualification\Actions\QualificationAuthorityLedger;
use Illuminate\Database\QueryException;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Str;
use Symfony\Component\HttpKernel\Exception\HttpException;

/**
 * E2 transactional authority tests. These use real PostgreSQL and an isolated
 * disposable database, but intentionally do not manufacture E3 reviewer evidence.
 */
beforeEach(function (): void {
    if (getenv('ASSURANCE_AUTHORITY_TEST_DATABASE') !== '1') {
        $this->markTestSkipped('Dedicated disposable PostgreSQL authority lane required.');
    }

    config([
        'database.default' => 'pgsql',
        'database.connections.pgsql.host' => '127.0.0.1',
        'database.connections.pgsql.port' => '5432',
        'database.connections.pgsql.database' => 'assurance',
        'database.connections.pgsql.username' => 'assurance_runtime',
        'database.connections.pgsql.password' => getenv('ASSURANCE_AUTHORITY_TEST_PASSWORD'),
        'database.connections.pgsql.sslmode' => 'prefer',
        'database.connections.pgsql.sslrootcert' => null,
    ]);
    DB::purge('pgsql');
    $this->scope = [
        'tenant_id' => (string) Str::uuid(),
        'site_id' => (string) Str::uuid(),
        'endpoint_id' => (string) Str::uuid(),
        'native_scope' => 'project:transactional-authority-fixture',
        'installed_tuple' => ['platform' => 'openstack'],
        'action' => 'application.provision',
        'method' => 'native_api',
        'profile_digest' => str_repeat('a', 64),
        'artifacts' => ['adapter' => str_repeat('b', 64)],
    ];
    $this->ledger = new QualificationAuthorityLedger;
});

it('serializes publication and holds the exact authority epoch with durable outbox evidence', function (): void {
    $command = (string) Str::uuid();
    $bundle = ['source' => 'e2-fixture'];
    $initial = $this->ledger->mutate(
        $this->scope, 'publish', $command, 0, 'E2-only review fixture',
        $bundle, str_repeat('a', 64), 1, 'reviewer-one'
    );

    expect($initial['state'])->toBe('qualified')
        ->and($initial['authority_epoch'])->toBe(1)
        ->and($this->ledger->current($this->scope)['authority_epoch'])->toBe(1);

    $retry = $this->ledger->mutate(
        $this->scope, 'publish', $command, 0, 'E2-only review fixture',
        $bundle, str_repeat('a', 64), 1, 'reviewer-one'
    );
    expect($retry)->toBe($initial);

    $scopeHash = \App\Domain\Qualification\NativeQualification::digest($this->scope);
    expect(DB::table('app.qualification_authority_events')->where('scope_sha256', $scopeHash)->count())->toBe(1)
        ->and(DB::table('app.qualification_authority_outbox')->where('scope_sha256', $scopeHash)->count())->toBe(1);

    try {
        $this->ledger->mutate(
            $this->scope, 'publish', $command, 0, 'changed retry',
            $bundle, str_repeat('a', 64), 1, 'reviewer-one'
        );
        $this->fail('Conflicting command ID was accepted.');
    } catch (HttpException $error) {
        expect($error->getStatusCode())->toBe(409);
    }
});

it('keeps suspension sticky and requires a distinct superseding signed decision for restoration', function (): void {
    $this->ledger->mutate(
        $this->scope, 'publish', (string) Str::uuid(), 0, 'fixture',
        ['source' => 'e2'], str_repeat('a', 64), 1, 'reviewer-one'
    );
    $held = $this->ledger->mutate(
        $this->scope, 'suspend', (string) Str::uuid(), 1, 'native contradiction',
        null, '', 0, 'native-observer'
    );
    expect($held['state'])->toBe('suspended')->and($held['authority_epoch'])->toBe(2);

    $repeat = $this->ledger->mutate(
        $this->scope, 'suspend', (string) Str::uuid(), 2, 'repeat negative probe',
        null, '', 0, 'native-observer'
    );
    expect($repeat['authority_epoch'])->toBe(2);

    try {
        $this->ledger->mutate(
            $this->scope, 'restore', (string) Str::uuid(), 2, 'same reviewer forbidden',
            ['source' => 'new-e2'], str_repeat('c', 64), 2, 'reviewer-one'
        );
        $this->fail('Non-independent restoration was accepted.');
    } catch (HttpException $error) {
        expect($error->getStatusCode())->toBe(409);
    }

    $restored = $this->ledger->mutate(
        $this->scope, 'restore', (string) Str::uuid(), 2, 'new independent review',
        ['source' => 'new-e2'], str_repeat('c', 64), 2, 'reviewer-two'
    );
    expect($restored['state'])->toBe('qualified')->and($restored['authority_epoch'])->toBe(3);

    $scopeHash = \App\Domain\Qualification\NativeQualification::digest($this->scope);
    $events = DB::table('app.qualification_authority_events')
        ->where('scope_sha256', $scopeHash)->orderBy('authority_epoch')->get();
    expect($events)->toHaveCount(3)
        ->and($events[1]->previous_event_sha256)->toBe($events[0]->event_sha256)
        ->and($events[2]->previous_event_sha256)->toBe($events[1]->event_sha256);

    try {
        $this->ledger->mutate(
            $this->scope, 'revoke', (string) Str::uuid(), 2, 'stale epoch',
            null, '', 0, 'reviewer-three'
        );
        $this->fail('Stale publication epoch was accepted.');
    } catch (HttpException $error) {
        expect($error->getStatusCode())->toBe(409);
    }
});

it('prevents runtime alteration or deletion of committed authority history', function (): void {
    $this->ledger->mutate(
        $this->scope, 'publish', (string) Str::uuid(), 0, 'fixture',
        ['source' => 'e2'], str_repeat('a', 64), 1, 'reviewer-one'
    );
    $scopeHash = \App\Domain\Qualification\NativeQualification::digest($this->scope);

    try {
        DB::table('app.qualification_authority_heads')
            ->where('scope_sha256', $scopeHash)->update(['authority_epoch' => 0]);
        $this->fail('Monotonic epoch guard was bypassed.');
    } catch (QueryException) {
        // Trigger rejects an epoch rewind.
    }

    try {
        DB::table('app.qualification_authority_events')
            ->where('scope_sha256', $scopeHash)->delete();
        $this->fail('Immutable event history was deleted.');
    } catch (QueryException) {
        // Runtime grants and append-only trigger prohibit deletion.
    }
    expect($this->ledger->current($this->scope)['authority_epoch'])->toBe(1);
});


it('delivers immutable invalidations in order and does not clear uncertain acknowledgments', function (): void {
    $this->ledger->mutate(
        $this->scope, 'publish', (string) Str::uuid(), 0, 'reviewed fixture',
        ['source' => 'e2'], str_repeat('a', 64), 1, 'reviewer-one'
    );
    $this->ledger->mutate(
        $this->scope, 'suspend', (string) Str::uuid(), 1, 'native contradiction',
        null, '', 0, 'native-observer'
    );
    $scopeHash = \App\Domain\Qualification\NativeQualification::digest($this->scope);
    $publisher = new class implements \App\Application\Qualification\Contracts\ConfirmedInvalidationPublisher
    {
        /** @var list<array<string, mixed>> */
        public array $accepted = [];

        public bool $unavailable = true;

        public function publish(array $event): void
        {
            if ($this->unavailable) {
                throw new \RuntimeException('receiving_inbox_unavailable');
            }
            $this->accepted[] = $event;
        }
    };
    $delivery = new \App\Application\Qualification\Actions\DeliverQualificationInvalidation($publisher);

    try {
        $delivery->handle();
        $this->fail('Unconfirmed event cleared the durable outbox.');
    } catch (\RuntimeException $error) {
        expect($error->getMessage())->toBe('receiving_inbox_unavailable');
    }
    expect(DB::table('app.qualification_authority_outbox')
        ->where('scope_sha256', $scopeHash)->whereNotNull('delivered_at')->count())->toBe(0);

    $publisher->unavailable = false;
    expect($delivery->handle())->toBe('delivered')
        ->and($delivery->handle())->toBe('delivered')
        ->and($delivery->handle())->toBe('idle');
    expect(array_column($publisher->accepted, 'authority_epoch'))->toBe([1, 2])
        ->and(DB::table('app.qualification_authority_outbox')
            ->where('scope_sha256', $scopeHash)->whereNotNull('delivered_at')->count())->toBe(2);
});
