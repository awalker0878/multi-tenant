<?php

declare(strict_types=1);

namespace App\Console\Commands;

use App\Application\Recovery\Actions\ApplyIdentityRecovery;
use App\Application\Recovery\Actions\ConfirmIdentityResumption;
use App\Application\Recovery\Actions\PrepareIdentityRecovery;
use App\Application\Recovery\Actions\PrepareIdentityResumption;
use App\Domain\Recovery\RecoveryDenied;
use App\Domain\Recovery\RecoveryJson;
use Illuminate\Console\Command;

final class RecoverIdentity extends Command
{
    protected $signature = 'identity:recovery {operation : prepare, apply, resume-plan or confirm} {--input= : Absolute private observations or signed envelope path} {--recovery-id= : Applied recovery UUID} {--output= : New absolute private result path}';

    protected $description = 'Perform separately authorized held identity reconciliation; never activate admission or reset bootstrap';

    public function handle(PrepareIdentityRecovery $prepare, ApplyIdentityRecovery $apply, PrepareIdentityResumption $resume, ConfirmIdentityResumption $confirm): int
    {
        $file = null;
        $path = $this->option('output');
        try {
            if (! is_string($path) || ! str_starts_with($path, '/') || str_contains($path, "\0") || ! is_dir(dirname($path))
                || (fileperms(dirname($path)) & 0077) !== 0 || is_link(dirname($path))) {
                throw new RecoveryDenied;
            }
            // Reserve output before changing DB state; never overwrite or follow a symlink.
            $file = @fopen($path, 'x');
            if ($file === false || ! chmod($path, 0600)) {
                throw new RecoveryDenied;
            }
            $result = match ($this->argument('operation')) {
                'prepare' => $prepare->handle(RecoveryJson::decode($this->inputBytes())),
                'apply' => $apply->handle($this->inputBytes()),
                'resume-plan' => $resume->handle((string) $this->option('recovery-id')),
                'confirm' => $confirm->handle($this->inputBytes()),
                default => throw new RecoveryDenied,
            };
            $wire = RecoveryJson::encode($result)."\n";
            if (fwrite($file, $wire) !== strlen($wire) || ! fflush($file) || ! fsync($file)) {
                throw new RecoveryDenied;
            }
            $this->info('Recovery result retained. Admission remains held until the independent custody release.');

            return self::SUCCESS;
        } catch (\Throwable) {
            // Never print SQL parameters, provider data, paths, packets or credentials.
            $this->error('identity_recovery_held: verify custody, signatures, exact state and output; do not retry by editing state.');

            return self::FAILURE;
        } finally {
            if (is_resource($file)) {
                fclose($file);
            }
        }
    }

    private function inputBytes(): string
    {
        $path = $this->option('input');
        if (! is_string($path) || ! str_starts_with($path, '/') || str_contains($path, "\0") || is_link($path)
            || ! is_file($path) || (fileperms($path) & 0077) !== 0) {
            throw new RecoveryDenied;
        }
        $wire = file_get_contents($path, false, null, 0, 131073);
        if (! is_string($wire) || strlen($wire) > 131072) {
            throw new RecoveryDenied;
        }

        return rtrim($wire, "\n");
    }
}
