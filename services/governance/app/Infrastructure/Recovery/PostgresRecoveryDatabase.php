<?php

declare(strict_types=1);

namespace App\Infrastructure\Recovery;

use App\Application\Recovery\Contracts\RecoveryDatabase;
use App\Domain\Recovery\RecoveryDenied;
use App\Domain\Support\SupportTrustState;
use Closure;
use Illuminate\Support\Facades\DB;

final class PostgresRecoveryDatabase implements RecoveryDatabase
{
    public function observe(Closure $read): SupportTrustState
    {
        if (DB::getDriverName() !== 'pgsql' || DB::transactionLevel() !== 0) {
            throw new RecoveryDenied;
        }
        DB::statement('SET ROLE governance_owner');
        try {
            return $read();
        } finally {
            DB::statement('RESET ROLE');
        }
    }

    public function lock(): void
    {
        if (DB::getDriverName() !== 'pgsql' || DB::transactionLevel() !== 1) {
            throw new RecoveryDenied;
        }
        // Only separately supplied migration-owner credentials can enter recovery.
        // The application runtime cannot SET this role or change a bound epoch.
        DB::statement('SET LOCAL ROLE governance_owner');
        DB::statement("SET LOCAL lock_timeout = '5s'");
        DB::statement("SET LOCAL statement_timeout = '60s'");
        foreach ($this->tables() as $table) {
            DB::statement('LOCK TABLE app.'.$table.' IN ACCESS EXCLUSIVE MODE');
        }
    }

    public function tables(): array
    {
        $tables = [];
        foreach (DB::select("SELECT tablename FROM pg_catalog.pg_tables WHERE schemaname = 'app' ORDER BY tablename") as $row) {
            if (! is_string($row->tablename) || preg_match('/\A[a-z][a-z_]{0,62}\z/', $row->tablename) !== 1) {
                throw new RecoveryDenied;
            }
            $tables[] = $row->tablename;
        }
        if (! in_array('identity_recovery_receipts', $tables, true) || count($tables) > 100) {
            throw new RecoveryDenied;
        }

        return $tables;
    }
}
