<?php

declare(strict_types=1);

namespace App\Infrastructure\Foundation;

use App\Application\Foundation\Contracts\DependencyProbe;
use Illuminate\Contracts\Config\Repository;
use PDO;
use Throwable;

final class PostgresDependencyProbe implements DependencyProbe
{
    public function __construct(
        private readonly Repository $config,
        private readonly MountedSecret $secrets,
    ) {}

    public function healthy(): bool
    {
        $host = $this->config->get('foundation.database.host');
        $port = $this->config->get('foundation.database.port');
        $database = $this->config->get('foundation.database.database');
        $username = $this->config->get('foundation.database.username');
        $certificate = $this->config->get('foundation.database.sslrootcert');
        $password = $this->secrets->read($this->config->get('foundation.database.password_file'));

        if (! is_string($host) || ! preg_match('/\A[A-Za-z0-9_.:-]{1,253}\z/', $host)
            || ! is_scalar($port) || ! ctype_digit((string) $port) || (int) $port < 1 || (int) $port > 65535
            || ! is_string($database) || ! preg_match('/\A[a-z_][a-z0-9_]{0,62}\z/', $database)
            || ! is_string($username) || ! preg_match('/\A[a-z_][a-z0-9_]{0,62}\z/', $username)
            || ! is_string($certificate) || ! preg_match('~\A/[A-Za-z0-9_./-]+\z~', $certificate)
            || ! is_file($certificate) || ! is_readable($certificate) || $password === null
            || $this->config->get('foundation.database.sslmode') !== 'verify-full') {
            return false;
        }

        try {
            // Fresh non-persistent sessions observe credential rotation and avoid pooled authority.
            $connection = new PDO(
                "pgsql:host={$host};port={$port};dbname={$database};sslmode=verify-full;sslrootcert={$certificate};connect_timeout=2",
                $username,
                $password,
                [PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION, PDO::ATTR_PERSISTENT => false],
            );
            $connection->exec('SET statement_timeout = 2000');
            $connection->exec('SET default_transaction_read_only = on');
            $statement = $connection->query('SELECT 1 AS probe, current_user AS identity, (SELECT count(*) FROM app.foundation_schema) AS schema_rows, (SELECT max(version) FROM app.foundation_schema) AS schema_version');
            $result = $statement === false ? false : $statement->fetch(PDO::FETCH_ASSOC);

            return is_array($result)
                && (int) $result['probe'] === 1
                && $result['identity'] === $username
                && (int) $result['schema_rows'] === 1
                && (int) $result['schema_version'] === 1;
        } catch (Throwable) {
            // Do not return or log PDO messages: they can contain credentials and topology.
            return false;
        }
    }
}
