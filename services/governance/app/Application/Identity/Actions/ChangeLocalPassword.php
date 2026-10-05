<?php

declare(strict_types=1);

namespace App\Application\Identity\Actions;

use App\Application\Identity\Data\SessionCredentials;
use App\Domain\Identity\BootstrapAdministrator;
use App\Domain\Identity\IdentityDenied;
use App\Domain\Identity\IdentityLedger;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Hash;

final class ChangeLocalPassword
{
    public function __construct(private readonly ResolveLocalSession $resolve, private readonly IssueLocalSession $sessions) {}

    public function handle(#[\SensitiveParameter] string $token, #[\SensitiveParameter] string $currentPassword, #[\SensitiveParameter] string $newPassword): SessionCredentials
    {
        $result = DB::transaction(function () use ($token, $currentPassword, $newPassword): SessionCredentials|IdentityDenied {
            $administrator = BootstrapAdministrator::query()->lockForUpdate()->findOrFail(1);
            $this->resolve->handle($token);
            if ($administrator->locked_until?->isFuture()) {
                return new IdentityDenied('temporarily_locked', 429);
            }
            if (! Hash::check($currentPassword, (string) $administrator->password_hash)) {
                $attempts = $administrator->failed_attempts + 1;
                $locked = $attempts >= (int) config('identity.max_attempts');
                $administrator->forceFill([
                    'failed_attempts' => $locked ? 0 : $attempts,
                    'locked_until' => $locked ? now()->addSeconds((int) config('identity.lock_seconds')) : null,
                ])->save();
                IdentityLedger::record('identity.password.denied');

                return new IdentityDenied('invalid_credentials');
            }
            if (mb_strlen($newPassword) < 15 || mb_strlen($newPassword) > 128 || strlen($newPassword) > 512 || str_contains($newPassword, "\0")
                || Hash::check($newPassword, (string) $administrator->password_hash)) {
                return new IdentityDenied('password_policy', 422);
            }
            $administrator->forceFill([
                'password_hash' => Hash::make($newPassword), 'state' => 'local_setup',
                'credential_version' => $administrator->credential_version + 1,
                'password_changed_at' => now(), 'failed_attempts' => 0, 'locked_until' => null,
            ])->save();
            DB::table('app.identity_sessions')->whereNull('revoked_at')->update(['revoked_at' => now()]);
            IdentityLedger::record('identity.password.changed');

            return $this->sessions->handle($administrator);
        });
        if ($result instanceof IdentityDenied) {
            throw $result;
        }

        return $result;
    }
}
