<?php

declare(strict_types=1);

namespace App\Infrastructure\Recovery;

use App\Application\Recovery\Contracts\RecoveryCustody;
use App\Domain\Recovery\RecoveryContext;
use App\Domain\Recovery\RecoveryDenied;
use App\Domain\Recovery\RecoveryJson;
use App\Infrastructure\Foundation\MountedSecret;

final class MountedRecoveryCustody implements RecoveryCustody
{
    public function held(): RecoveryContext
    {
        $wire = (new MountedSecret)->read(config('identity.admission_file'));
        $descriptor = $wire === null ? null : json_decode($wire, true, 8);
        if (! is_array($descriptor) || count($descriptor) !== 5 || ($descriptor['version'] ?? null) !== 1
            || ($descriptor['state'] ?? null) !== 'held' || ($descriptor['bootstrap_allowed'] ?? null) !== false
            || ! RecoveryJson::uuid($descriptor['installation_id'] ?? null) || ! RecoveryJson::hash($descriptor['epoch'] ?? null)) {
            throw new RecoveryDenied;
        }
        $trust = $this->trust();
        if ($trust['installation_id'] !== $descriptor['installation_id']) {
            throw new RecoveryDenied;
        }
        $paths = ['console' => config('identity.console_credential_file'), ...config('identity.service_credentials')];
        $workloads = [];
        foreach ($paths as $name => $path) {
            $secret = $path === null ? null : (new MountedSecret)->read($path);
            if (($path !== null || $name === 'console') && ($secret === null || strlen($secret) < 32)) {
                throw new RecoveryDenied;
            }
            $workloads[$name] = $secret === null ? null : hash('sha256', $secret);
        }

        return new RecoveryContext($descriptor['installation_id'], hash('sha256', $descriptor['installation_id'].':'.$descriptor['epoch']),
            hash('sha256', (string) $wire), RecoveryJson::digest($trust), $workloads, $this->code());
    }

    public function authorize(string $envelope, string $purpose): array
    {
        if (strlen($envelope) > 131072) {
            throw new RecoveryDenied;
        }
        $packet = RecoveryJson::decode($envelope);
        $encoded = $packet['payload'] ?? null;
        $signatures = $packet['signatures'] ?? null;
        if (count($packet) !== 2 || ! is_string($encoded) || ! is_array($signatures) || ! array_is_list($signatures) || count($signatures) !== 2) {
            throw new RecoveryDenied;
        }
        $wire = base64_decode($encoded, true);
        if ($wire === false || base64_encode($wire) !== $encoded || strlen($wire) > 65536) {
            throw new RecoveryDenied;
        }
        $payload = RecoveryJson::decode($wire);
        $trust = $this->trust();
        $now = now()->getTimestamp();
        if (($payload['version'] ?? null) !== 1 || ($payload['purpose'] ?? null) !== $purpose
            || ($payload['installation_id'] ?? null) !== $trust['installation_id']
            || ($payload['trust_sha256'] ?? null) !== RecoveryJson::digest($trust)
            || ! is_int($payload['created_at'] ?? null) || ! is_int($payload['expires_at'] ?? null)
            || $payload['created_at'] > $now || $payload['expires_at'] <= $now
            || $payload['expires_at'] - $payload['created_at'] > 900 || $payload['created_at'] >= $payload['expires_at']) {
            throw new RecoveryDenied;
        }
        $principals = [];
        foreach ($signatures as $signature) {
            if (! is_array($signature) || count($signature) !== 2 || ! is_string($signature['principal_id'] ?? null)
                || ! is_string($signature['signature'] ?? null) || in_array($signature['principal_id'], $principals, true)) {
                throw new RecoveryDenied;
            }
            $principal = null;
            foreach ($trust['principals'] as $candidate) {
                if ($candidate['id'] === $signature['principal_id']) {
                    $principal = $candidate;
                }
            }
            $bytes = base64_decode($signature['signature'], true);
            if ($principal === null || $bytes === false || strlen($bytes) > 1024
                || base64_encode($bytes) !== $signature['signature']
                || @openssl_verify(RecoveryJson::DOMAIN.$wire, $bytes, $principal['public_key_pem'], OPENSSL_ALGO_SHA256) !== 1) {
                throw new RecoveryDenied;
            }
            $principals[] = $signature['principal_id'];
        }

        return ['payload' => $payload, 'principals' => $principals];
    }

    /** @return array{version: int, installation_id: string, valid_from: int, valid_until: int, principals: list<array{id: string, role: string, public_key_pem: string}>} */
    private function trust(): array
    {
        $path = config('identity.recovery_trust_file');
        if (is_string($path)) {
            clearstatcache(true, $path);
        }
        if (! is_string($path) || ! str_starts_with($path, '/') || str_contains($path, "\0") || is_link($path)
            || ! is_file($path) || (fileperms($path) & 0022) !== 0) {
            throw new RecoveryDenied;
        }
        $wire = @file_get_contents($path, false, null, 0, 32769);
        if (! is_string($wire) || strlen($wire) > 32768) {
            throw new RecoveryDenied;
        }
        $trust = RecoveryJson::decode(rtrim($wire, "\n"));
        if (count($trust) !== 5 || ($trust['version'] ?? null) !== 1 || ! is_string($trust['installation_id'] ?? null) || ! RecoveryJson::uuid($trust['installation_id'])
            || ! is_int($trust['valid_from'] ?? null) || ! is_int($trust['valid_until'] ?? null)
            || $trust['valid_from'] > now()->getTimestamp() || $trust['valid_until'] <= now()->getTimestamp()
            || ! is_array($trust['principals'] ?? null) || ! array_is_list($trust['principals']) || count($trust['principals']) !== 2) {
            throw new RecoveryDenied;
        }
        $ids = $keys = $roles = $validated = [];
        foreach ($trust['principals'] as $principal) {
            if (! is_array($principal) || count($principal) !== 3 || ! is_string($principal['id'] ?? null) || ! RecoveryJson::uuid($principal['id'])
                || ! is_string($principal['role'] ?? null) || ! in_array($principal['role'], ['recovery_owner', 'security_reviewer'], true)
                || ! is_string($principal['public_key_pem'] ?? null)) {
                throw new RecoveryDenied;
            }
            $key = @openssl_pkey_get_public($principal['public_key_pem']);
            $details = $key === false ? false : openssl_pkey_get_details($key);
            if ($details === false || $details['type'] !== OPENSSL_KEYTYPE_RSA || $details['bits'] < 3072 || $details['bits'] > 8192
                || in_array($principal['id'], $ids, true) || in_array($principal['role'], $roles, true) || in_array($details['key'], $keys, true)) {
                throw new RecoveryDenied;
            }
            $ids[] = $principal['id'];
            $roles[] = $principal['role'];
            $keys[] = $details['key'];
            $validated[] = ['id' => $principal['id'], 'role' => $principal['role'], 'public_key_pem' => $principal['public_key_pem']];
        }

        return ['version' => 1, 'installation_id' => $trust['installation_id'], 'valid_from' => $trust['valid_from'],
            'valid_until' => $trust['valid_until'], 'principals' => $validated];
    }

    private function code(): string
    {
        $files = [];
        foreach (['app', 'config', 'database/migrations', 'resources/contracts'] as $directory) {
            foreach (new \RecursiveIteratorIterator(new \RecursiveDirectoryIterator(base_path($directory), \FilesystemIterator::SKIP_DOTS)) as $file) {
                if ($file->isLink() || ! $file->isFile() || $file->getSize() > 16777216 || count($files) > 1000) {
                    throw new RecoveryDenied;
                }
                $files[substr($file->getPathname(), strlen(base_path()) + 1)] = hash_file('sha256', $file->getPathname());
            }
        }
        foreach (['artisan', 'composer.json', 'composer.lock', 'bootstrap/app.php', 'bootstrap/providers.php'] as $path) {
            $files[$path] = hash_file('sha256', base_path($path));
        }

        return RecoveryJson::digest($files);
    }
}
