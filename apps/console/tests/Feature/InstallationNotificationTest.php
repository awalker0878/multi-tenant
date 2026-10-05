<?php

declare(strict_types=1);

use App\Application\Notifications\Actions\RecordNotification;
use App\Domain\Notifications\InvalidNotification;
use App\Infrastructure\Notifications\GovernanceNotificationDecoder;
use App\Infrastructure\Notifications\PostgresNotificationHints;
use Illuminate\Database\QueryException;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Http;

beforeEach(function (): void {
    initializeNotificationFixture();
});

it('retains installation receipts in the shared immutable ID namespace without a tenant projection', function (): void {
    $record = app(RecordNotification::class);
    $delivery = installationDelivery();
    expect($record->handle($delivery))->toBe('recorded');
    $cursor = app(PostgresNotificationHints::class)->current('installation');
    expect($cursor)->not->toBeNull()->and(DB::table('app.notification_inbox')->first()->tenant_id)->toBeNull()
        ->and(DB::table('app.notification_hints')->count())->toBe(0)
        ->and($record->handle($delivery))->toBe('duplicate')
        ->and(app(PostgresNotificationHints::class)->current('installation'))->toBe($cursor)
        ->and($record->handle(tenantDelivery(['event_id' => $delivery->messageId])))->toBe('quarantined')
        ->and(DB::table('app.notification_inbox')->count())->toBe(1);
});

it('retains login receipts without changing the settings hint', function (): void {
    $record = app(RecordNotification::class);
    $record->handle(installationDelivery());
    $cursor = app(PostgresNotificationHints::class)->current('installation');
    expect($record->handle(installationDelivery(['event_type' => 'identity.login.succeeded'])))->toBe('recorded')
        ->and(app(PostgresNotificationHints::class)->current('installation'))->toBe($cursor);
});

it('rejects tenant substitution and untrusted identity event envelopes', function (array $body, array $properties): void {
    expect(fn () => app(GovernanceNotificationDecoder::class)->decode(installationDelivery($body, $properties)))
        ->toThrow(InvalidNotification::class);
})->with([
    [['scope' => 'tenant'], []], [['tenant_id' => '550e8400-e29b-41d4-a716-446655440001'], []],
    [['actor_kind' => 'federated', 'actor_id' => null], []], [['schema_version' => 2], []],
    [[], ['publisher' => 'console']], [[], ['routingKey' => 'governance.quota.changed.v1']],
    [[], ['messageId' => '550e8400-e29b-41d4-a716-446655440009']], [['client_secret' => 'never-project'], []],
]);

it('rolls back an installation receipt when its hint cannot commit', function (): void {
    DB::statement('DROP TABLE app.installation_notification_hint');
    expect(fn () => app(RecordNotification::class)->handle(installationDelivery()))->toThrow(QueryException::class)
        ->and(DB::table('app.notification_inbox')->count())->toBe(0);
});

it('checks current installation ownership before revealing a hint', function (int $ownerStatus): void {
    $credential = tempnam(sys_get_temp_dir(), 'p02-installation-');
    file_put_contents($credential, bin2hex(random_bytes(32)));
    config(['identity.governance_url' => 'https://governance.example.test', 'identity.credential_file' => $credential]);
    Http::preventStrayRequests();
    Http::fake([
        'governance.example.test/identity/session' => Http::response(['identity' => [
            'kind' => 'federated', 'subject' => '550e8400-e29b-41d4-a716-446655440000',
            'password_change_required' => false, 'permissions' => ['identity.logout'],
        ]]),
        'governance.example.test/identity/oidc' => Http::response($ownerStatus === 200 ? ['revision' => 1] : ['error' => 'denied'], $ownerStatus),
    ]);
    app(RecordNotification::class)->handle(installationDelivery());
    try {
        $response = $this->withSession(['identity.token' => str_repeat('a', 64), 'role' => 'installation_admin'])
            ->getJson('/setup/notification-status?scope=installation&role=administrator')->assertStatus($ownerStatus);
        if ($ownerStatus === 200) {
            $response->assertExactJson(['cursor' => app(PostgresNotificationHints::class)->current('installation')])
                ->assertHeader('Cache-Control', 'no-store, private');
        } else {
            expect($response->getContent())->not->toContain(app(PostgresNotificationHints::class)->current('installation'));
        }
    } finally {
        unlink($credential);
    }
})->with([200, 401, 403, 503]);

it('packages the identity schema without editing its published bytes', function (): void {
    expect(hash_file('sha256', resource_path('contracts/identity-change-v1.json')))
        ->toBe(hash_file('sha256', base_path('../../contracts/schemas/events/identity-change-v1.json')));
});
