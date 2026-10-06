<?php

declare(strict_types=1);

use App\Application\Identity\Actions\CheckIdentityAdmission;
use App\Application\Recovery\Actions\ApplyIdentityRecovery;
use App\Application\Recovery\Actions\ConfirmIdentityResumption;
use App\Application\Recovery\Actions\PrepareIdentityRecovery;
use App\Application\Recovery\Actions\PrepareIdentityResumption;
use App\Application\Recovery\Contracts\RecoveryCustody;
use App\Application\Recovery\RecoveryState;
use App\Domain\Identity\IdentityDenied;
use App\Domain\Recovery\RecoveryDenied;
use App\Domain\Recovery\RecoveryJson;
use Illuminate\Database\QueryException;
use Illuminate\Support\Facades\DB;

require_once __DIR__.'/../Support/RecoveryFixture.php';

beforeEach(function (): void {
    initializeRecoveryFixture($this);
});

afterEach(function (): void {
    if (DB::getDriverName() === 'pgsql') {
        // This fixture's owner has only grants in the disposable p02_identity_test DB.
        DB::unprepared('DROP OWNED BY governance_owner; DROP ROLE governance_owner;');
    }
    foreach (glob($this->recoveryDirectory.'/*') as $path) {
        unlink($path);
    }
    rmdir($this->recoveryDirectory);
    unlink($this->credentialFile);
    $this->travelBack();
});

it('reconciles under dual signatures and requires a second approved release before fresh federated resumption', function (): void {
    $beforeAudit = DB::table('app.support_audit')->count();
    $plan = app(PrepareIdentityRecovery::class)->handle($this->observations);
    $receipt = app(ApplyIdentityRecovery::class)->handle(recoveryEnvelope($this, $plan));
    expect($receipt['admission'])->toBe('HELD')
        ->and(DB::table('app.federated_sessions')->whereNull('revoked_at')->count())->toBe(0)
        ->and(DB::table('app.identity_sessions')->whereNull('revoked_at')->count())->toBe(0)
        ->and(DB::table('app.support_security_grants')->whereNull('revoked_at')->count())->toBe(0)
        ->and(DB::table('app.delegated_grants')->whereNull('revoked_at')->count())->toBe(0)
        ->and(DB::table('app.actor_delegations')->whereNull('revoked_at')->count())->toBe(0)
        ->and(DB::table('app.approvals')->value('state'))->toBe('revoked')
        ->and(DB::table('app.oidc_flows')->whereNull('consumed_at')->count())->toBe(0)
        ->and(DB::table('app.support_requests')->value('state'))->toBe('invalidated')
        ->and(DB::table('app.support_audit')->count())->toBe($beforeAudit + 1)
        ->and(DB::table('app.support_audit')->count())->toBe(DB::table('app.support_outbox')->count())
        ->and(DB::table('app.tenant_memberships')->where('state', 'active')->pluck('id')->all())->toBe([$this->ownerMembership])
        ->and(DB::table('app.tenants')->where('id', $this->otherTenant)->value('state'))->toBe('suspended')
        ->and(DB::table('app.bootstrap_administrator')->value('state'))->toBe('retired');
    // Even an accidental early opening of the external descriptor cannot bypass confirmation.
    $this->admission['state'] = 'active';
    file_put_contents($this->admissionFile, RecoveryJson::encode($this->admission));
    expect(fn () => app(CheckIdentityAdmission::class)->handle())->toThrow(IdentityDenied::class);
    $this->admission['state'] = 'held';
    file_put_contents($this->admissionFile, RecoveryJson::encode($this->admission));
    $resume = app(PrepareIdentityResumption::class)->handle($plan['recovery_id']);
    $confirmed = app(ConfirmIdentityResumption::class)->handle(recoveryEnvelope($this, $resume));
    expect($confirmed['admission'])->toBe('HELD_CONFIRMED')
        ->and(fn () => app(CheckIdentityAdmission::class)->handle())->toThrow(IdentityDenied::class);
    $this->admission['state'] = 'active';
    file_put_contents($this->admissionFile, RecoveryJson::encode($this->admission));
    app(CheckIdentityAdmission::class)->handle();
    $this->withHeader('X-Console-Session', $this->owner)->getJson('/identity/session')->assertUnauthorized();
    $this->postJson('/identity/local-sessions', ['username' => 'admin', 'password' => $this->temporary])->assertUnauthorized();
    $fresh = federatedLogin($this, 'support-tenant-owner');
    $this->withHeader('X-Console-Session', $fresh)->getJson('/v1/tenants/'.$this->tenant)->assertOk();
    $this->getJson('/v1/tenants/'.$this->otherTenant)->assertNotFound();
    $this->withHeader('Authorization', 'Bearer '.$this->previousWorkload)->getJson('/identity/session')->assertUnauthorized();
});

it('rejects missing duplicated modified expired wrong-purpose or foreign recovery signatures without mutation', function (string $fault): void {
    $plan = app(PrepareIdentityRecovery::class)->handle($this->observations);
    if ($fault === 'expired') {
        $plan['created_at'] -= 901;
        $plan['expires_at'] -= 901;
    } elseif ($fault === 'future') {
        $plan['created_at'] += 60;
        $plan['expires_at'] += 60;
    } elseif ($fault === 'purpose') {
        $plan['purpose'] = 'resume';
    } elseif ($fault === 'installation') {
        $plan['installation_id'] = '550e8400-e29b-41d4-a716-446655440099';
    }
    $packet = RecoveryJson::decode(recoveryEnvelope($this, $plan));
    if ($fault === 'missing') {
        array_pop($packet['signatures']);
    } elseif ($fault === 'duplicate') {
        $packet['signatures'][1] = $packet['signatures'][0];
    } elseif ($fault === 'tamper') {
        $packet['signatures'][0]['signature'] = base64_encode(str_repeat('x', 384));
    }
    $before = app(RecoveryState::class)->snapshot();
    expect(fn () => app(ApplyIdentityRecovery::class)->handle(RecoveryJson::encode($packet)))->toThrow(RecoveryDenied::class)
        ->and(app(RecoveryState::class)->snapshot())->toBe($before);
})->with(['missing', 'duplicate', 'tamper', 'expired', 'future', 'purpose', 'installation']);

it('denies state key custody descriptor credential or current issuer changes after approval', function (string $fault): void {
    $plan = app(PrepareIdentityRecovery::class)->handle($this->observations);
    $envelope = recoveryEnvelope($this, $plan);
    if ($fault === 'database') {
        DB::table('app.tenants')->where('id', $this->tenant)->increment('revision');
    } elseif ($fault === 'descriptor') {
        $this->admission['epoch'] = bin2hex(random_bytes(32));
        file_put_contents($this->admissionFile, RecoveryJson::encode($this->admission));
    } elseif ($fault === 'credential') {
        file_put_contents($this->credentialFile, bin2hex(random_bytes(32)));
    } elseif ($fault === 'key-custody') {
        DB::table('app.identity_secrets')->update(['ciphertext' => 'not-decryptable']);
    } elseif ($fault === 'trust') {
        $this->recoveryTrust['valid_until']++;
        file_put_contents($this->trustFile, RecoveryJson::encode($this->recoveryTrust));
    } else {
        $this->provider->keyOverride = [];
    }
    $before = app(RecoveryState::class)->snapshot();
    expect(fn () => app(ApplyIdentityRecovery::class)->handle($envelope))->toThrow(in_array($fault, ['key-custody', 'issuer'], true) ? IdentityDenied::class : RecoveryDenied::class)
        ->and(app(RecoveryState::class)->snapshot())->toBe($before)
        ->and(DB::table('app.identity_admission')->value('binding_sha256'))->toBe($this->priorBinding);
})->with(['database', 'descriptor', 'credential', 'key-custody', 'trust', 'issuer']);

it('denies unrotated workload credentials and unreviewed orphaned or revoked memberships', function (string $fault): void {
    $observations = $this->observations;
    if ($fault === 'credential') {
        file_put_contents($this->credentialFile, $this->previousWorkload);
    } elseif ($fault === 'evidence') {
        unset($observations['records_sha256']);
    } elseif ($fault === 'orphan') {
        $observations['memberships'] = [['id' => $this->targetMembership['id'], 'owner_record_sha256' => hash('sha256', 'owner')]];
    } elseif ($fault === 'revoked') {
        DB::table('app.tenant_memberships')->where('id', $this->ownerMembership)->update(['state' => 'revoked']);
    } else {
        DB::table('app.bootstrap_administrator')->update(['state' => 'uninitialized', 'password_hash' => null]);
    }
    expect(fn () => app(PrepareIdentityRecovery::class)->handle($observations))->toThrow(RecoveryDenied::class)
        ->and(DB::table('app.identity_recovery_receipts')->count())->toBe(0);
})->with(['credential', 'evidence', 'orphan', 'revoked', 'bootstrap']);

it('rejects shared workload credentials before preparing recovery authority', function (): void {
    config(['identity.service_credentials.catalogue' => $this->credentialFile]);
    expect(fn () => app(PrepareIdentityRecovery::class)->handle($this->observations))->toThrow(RecoveryDenied::class)
        ->and(DB::table('app.identity_recovery_receipts')->count())->toBe(0);
});

it('rolls back every revocation if immutable recovery receipt retention fails', function (): void {
    $plan = app(PrepareIdentityRecovery::class)->handle($this->observations);
    $before = app(RecoveryState::class)->snapshot();
    if (DB::getDriverName() === 'pgsql') {
        DB::statement('ALTER TABLE app.identity_recovery_receipts ADD CONSTRAINT force_test_failure CHECK (false)');
    } else {
        DB::unprepared("CREATE TRIGGER app.reject_recovery BEFORE INSERT ON identity_recovery_receipts BEGIN SELECT RAISE(ABORT, 'synthetic_failure'); END;");
    }
    expect(fn () => app(ApplyIdentityRecovery::class)->handle(recoveryEnvelope($this, $plan)))->toThrow(QueryException::class)
        ->and(app(RecoveryState::class)->snapshot())->toBe($before)
        ->and(DB::table('app.identity_admission')->value('binding_sha256'))->toBe($this->priorBinding);
});

it('rejects replay and any post-reconciliation changes before confirming resumption', function (): void {
    $plan = app(PrepareIdentityRecovery::class)->handle($this->observations);
    $envelope = recoveryEnvelope($this, $plan);
    app(ApplyIdentityRecovery::class)->handle($envelope);
    expect(fn () => app(ApplyIdentityRecovery::class)->handle($envelope))->toThrow(RecoveryDenied::class);
    $resume = app(PrepareIdentityResumption::class)->handle($plan['recovery_id']);
    DB::table('app.tenants')->where('id', $this->tenant)->increment('revision');
    expect(fn () => app(ConfirmIdentityResumption::class)->handle(recoveryEnvelope($this, $resume)))->toThrow(RecoveryDenied::class)
        ->and(DB::table('app.identity_recovery_releases')->count())->toBe(0);
});

it('never accepts duplicate principal IDs same-key roles revoked policy or writable trust material', function (string $fault): void {
    if ($fault === 'same-id') {
        $this->recoveryTrust['principals'][1]['id'] = $this->recoveryTrust['principals'][0]['id'];
    } elseif ($fault === 'same-key') {
        $this->recoveryTrust['principals'][1]['public_key_pem'] = $this->recoveryTrust['principals'][0]['public_key_pem'];
    } elseif ($fault === 'expired') {
        $this->recoveryTrust['valid_until'] = now()->getTimestamp();
    }
    file_put_contents($this->trustFile, RecoveryJson::encode($this->recoveryTrust));
    if ($fault === 'writable') {
        chmod($this->trustFile, 0660);
        clearstatcache();
    }
    expect(fn () => app(RecoveryCustody::class)->held())->toThrow(RecoveryDenied::class);
})->with(['same-id', 'same-key', 'expired', 'writable']);
