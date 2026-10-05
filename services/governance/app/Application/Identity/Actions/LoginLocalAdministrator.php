<?php

declare(strict_types=1);

namespace App\Application\Identity\Actions;

use App\Application\Identity\Data\SessionCredentials;
use App\Domain\Identity\BootstrapAdministrator;
use App\Domain\Identity\IdentityDenied;
use App\Domain\Identity\IdentityLedger;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Hash;

final class LoginLocalAdministrator
{
    public function __construct(private readonly IssueLocalSession $sessions) {}

    public function handle(string $username, #[\SensitiveParameter] string $password): SessionCredentials
    {
        // Return denials from the transaction so failed-attempt state is committed.
        $result = DB::transaction(function () use ($username, $password): SessionCredentials|IdentityDenied {
            $administrator = BootstrapAdministrator::query()->lockForUpdate()->findOrFail(1);
            if (! $administrator->allowsLocalLogin()) {
                return new IdentityDenied('invalid_credentials');
            }
            if ($administrator->locked_until?->isFuture()) {
                return new IdentityDenied('temporarily_locked', 429);
            }
            $matches = Hash::check($password, (string) $administrator->password_hash);
            if ($username !== 'admin' || ! $matches) {
                $attempts = $administrator->failed_attempts + 1;
                $locked = $attempts >= (int) config('identity.max_attempts');
                $administrator->forceFill([
                    'failed_attempts' => $locked ? 0 : $attempts,
                    'locked_until' => $locked ? now()->addSeconds((int) config('identity.lock_seconds')) : null,
                ])->save();
                IdentityLedger::record('identity.login.denied', 'unauthenticated');

                return new IdentityDenied('invalid_credentials');
            }
            $administrator->forceFill(['failed_attempts' => 0, 'locked_until' => null])->save();
            IdentityLedger::record('identity.login.succeeded');

            return $this->sessions->handle($administrator);
        });
        if ($result instanceof IdentityDenied) {
            throw $result;
        }

        return $result;
    }
}
