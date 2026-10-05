<?php

declare(strict_types=1);

namespace App\Application\Identity\Actions;

use App\Domain\Identity\BootstrapAdministrator as Administrator;
use App\Domain\Identity\IdentityLedger;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Hash;

final class BootstrapAdministrator
{
    // The only plaintext return is consumed by the protected deployment terminal.
    public function handle(): ?string
    {
        return DB::transaction(function (): ?string {
            $administrator = Administrator::query()->lockForUpdate()->findOrFail(1);
            if ($administrator->state !== 'uninitialized') {
                return null;
            }
            $temporary = bin2hex(random_bytes(24));
            $administrator->forceFill([
                'password_hash' => Hash::make($temporary), 'state' => 'password_change_required',
                'credential_version' => 1, 'initialized_at' => now(),
            ])->save();
            IdentityLedger::record('identity.bootstrap.created', 'deployment');

            return $temporary;
        });
    }
}
