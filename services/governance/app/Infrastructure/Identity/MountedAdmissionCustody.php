<?php

declare(strict_types=1);

namespace App\Infrastructure\Identity;

use App\Application\Identity\Contracts\AdmissionCustody;
use App\Domain\Identity\AdmissionState;
use App\Domain\Identity\IdentityDenied;
use App\Infrastructure\Foundation\MountedSecret;

final class MountedAdmissionCustody implements AdmissionCustody
{
    public function current(): AdmissionState
    {
        // Read on every admission. No cached generation, environment value, or DB fallback.
        $wire = (new MountedSecret)->read(config('identity.admission_file'));
        $value = $wire === null ? null : json_decode($wire, true, 8);
        if (! is_array($value) || count($value) !== 5 || ($value['version'] ?? null) !== 1
            || ($value['state'] ?? null) !== 'active' || ! is_bool($value['bootstrap_allowed'] ?? null)
            || ! is_string($value['installation_id'] ?? null) || ! preg_match('/\A[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\z/', $value['installation_id'])
            || ! is_string($value['epoch'] ?? null) || ! preg_match('/\A[0-9a-f]{64}\z/', $value['epoch'])) {
            throw new IdentityDenied('identity_recovery_required', 503);
        }

        return new AdmissionState(hash('sha256', $value['installation_id'].':'.$value['epoch']), $value['bootstrap_allowed']);
    }
}
