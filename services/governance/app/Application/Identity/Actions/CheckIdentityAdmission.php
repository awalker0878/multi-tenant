<?php

declare(strict_types=1);

namespace App\Application\Identity\Actions;

use App\Application\Identity\Contracts\AdmissionCustody;
use App\Domain\Identity\IdentityDenied;
use Illuminate\Support\Facades\DB;

final class CheckIdentityAdmission
{
    public function __construct(private readonly AdmissionCustody $custody) {}

    public function handle(bool $initialize = false): void
    {
        $external = $this->custody->current();
        $stored = DB::table('app.identity_admission')->where('id', 1)->first();
        // Initialization is allowed only inside bootstrap's locked transaction.
        // Neither a startup nor a normal request can adopt restored authority.
        if ($initialize && DB::transactionLevel() > 0 && $external->bootstrapAllowed && $stored !== null && $stored->binding_sha256 === null
            && DB::table('app.bootstrap_administrator')->where('id', 1)->value('state') === 'uninitialized') {
            if (DB::getDriverName() === 'pgsql') {
                DB::select('SELECT app.bind_initial_identity_admission(?)', [$external->binding]);
            } else {
                DB::table('app.identity_admission')->where('id', 1)->whereNull('binding_sha256')->update(['binding_sha256' => $external->binding]);
            }
            $stored = DB::table('app.identity_admission')->where('id', 1)->first();
        }
        if (! is_string($stored?->binding_sha256) || ! hash_equals($stored->binding_sha256, $external->binding)) {
            throw new IdentityDenied('identity_recovery_required', 503);
        }
        $recovery = DB::table('app.identity_recovery_receipts')->where('binding_sha256', $external->binding)->value('id');
        if ($recovery !== null && ! DB::table('app.identity_recovery_releases')->where('id', $recovery)->exists()) {
            throw new IdentityDenied('identity_recovery_required', 503);
        }
    }
}
