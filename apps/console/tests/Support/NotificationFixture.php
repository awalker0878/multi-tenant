<?php

declare(strict_types=1);

use App\Application\Notifications\Data\Delivery;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Str;

function initializeNotificationFixture(): void
{
    if (getenv('P02_TEST_POSTGRES') === '1') {
        config(['database.connections.notification_test' => [
            'driver' => 'pgsql', 'host' => '127.0.0.1', 'port' => getenv('P02_TEST_PORT') ?: '5432',
            'database' => 'p02_identity_test', 'username' => 'postgres', 'password' => getenv('P02_TEST_PASSWORD'),
            'charset' => 'utf8', 'prefix' => '', 'sslmode' => 'prefer',
        ]]);
    } else {
        config(['database.connections.notification_test' => ['driver' => 'sqlite', 'database' => ':memory:', 'prefix' => '']]);
    }
    config(['database.default' => 'notification_test']);
    DB::purge('notification_test');
    if (DB::getDriverName() === 'pgsql') {
        DB::unprepared('DROP SCHEMA IF EXISTS app CASCADE; CREATE SCHEMA app');
    } else {
        DB::statement("ATTACH DATABASE ':memory:' AS app");
    }
    foreach (['002_notifications.sql', '003_installation_notifications.sql'] as $migration) {
        $sql = file_get_contents(database_path('migrations/'.$migration));
        $sql = preg_replace('/^\\\\.*$/m', '', $sql);
        $sql = preg_replace('/^(?:SET LOCAL ROLE|GRANT|REVOKE) [^;]+;\s*/m', '', $sql);
        if (DB::getDriverName() === 'sqlite') {
            $sql = str_replace('tenant_id uuid NOT NULL', 'tenant_id uuid', $sql);
            $sql = str_replace('ALTER TABLE app.notification_inbox ALTER COLUMN tenant_id DROP NOT NULL;', '', $sql);
        }
        DB::unprepared($sql);
    }
}

function tenantDelivery(array $overrides = [], array $properties = []): Delivery
{
    $event = array_replace([
        'event_type' => 'governance.quota.changed', 'schema_version' => 1, 'event_id' => (string) Str::uuid(),
        'tenant_id' => '550e8400-e29b-41d4-a716-446655440001', 'actor_id' => '550e8400-e29b-41d4-a716-446655440002',
        'actor_kind' => 'federated', 'resource_id' => '550e8400-e29b-41d4-a716-446655440003', 'revision' => 2,
        'audit_sha256' => str_repeat('a', 64), 'occurred_at' => '2026-10-05T10:00:00Z', 'authority_use' => 'notification_only',
    ], $overrides);

    return new Delivery(...array_replace([
        'wire' => json_encode($event, JSON_THROW_ON_ERROR), 'messageId' => $event['event_id'],
        'routingKey' => $event['event_type'].'.v1', 'publisher' => 'governance', 'contentType' => 'application/json',
    ], $properties));
}

function installationDelivery(array $overrides = [], array $properties = []): Delivery
{
    $event = array_replace([
        'event_type' => 'identity.oidc.settings_saved', 'schema_version' => 1, 'event_id' => (string) Str::uuid(),
        'scope' => 'installation', 'actor_id' => null, 'actor_kind' => 'bootstrap',
        'audit_sha256' => str_repeat('a', 64), 'occurred_at' => '2026-10-05T10:00:00Z', 'authority_use' => 'notification_only',
    ], $overrides);

    return new Delivery(...array_replace([
        'wire' => json_encode($event, JSON_THROW_ON_ERROR), 'messageId' => $event['event_id'],
        'routingKey' => $event['event_type'].'.v1', 'publisher' => 'governance', 'contentType' => 'application/json',
    ], $properties));
}
