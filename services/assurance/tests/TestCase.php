<?php

declare(strict_types=1);

namespace Tests;

use Illuminate\Foundation\Testing\TestCase as BaseTestCase;
use Illuminate\Support\Facades\DB;

abstract class TestCase extends BaseTestCase
{
    public function qualificationCommands(): void
    {
        if (getenv('ASSURANCE_AUTHORITY_TEST_DATABASE') === '1') {
            config(['database.default' => 'pgsql',
                'database.connections.pgsql.host' => '127.0.0.1',
                'database.connections.pgsql.port' => '5432',
                'database.connections.pgsql.database' => 'assurance',
                'database.connections.pgsql.username' => 'assurance_runtime',
                'database.connections.pgsql.password' => getenv('ASSURANCE_AUTHORITY_TEST_PASSWORD'),
                'database.connections.pgsql.sslmode' => 'prefer',
                'database.connections.pgsql.sslrootcert' => null,
            ]);
            DB::purge('pgsql');
        } else {
            config(['database.default' => 'qualification_test', 'database.connections.qualification_test' => [
                'driver' => 'sqlite', 'database' => ':memory:', 'prefix' => '',
            ]]);
            DB::purge('qualification_test');
            DB::statement("ATTACH DATABASE ':memory:' AS app");
            $migration = file_get_contents(__DIR__.'/../database/migrations/003_qualification_command_keys.sql');
            preg_match('/CREATE TABLE IF NOT EXISTS app\.qualification_command_keys \(.*?\);/s', $migration, $match);
            DB::statement($match[0]);
        }
        $this->withHeader('Idempotency-Key', bin2hex(random_bytes(32)));
    }
}
