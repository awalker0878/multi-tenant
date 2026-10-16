<?php

declare(strict_types=1);

use App\Application\Planning\Contracts\PlanningInputAuthority;
use Illuminate\Support\Facades\DB;

beforeEach(function (): void {
    $this->qualificationCommands();
    $this->id = '10000000-0000-4000-8000-000000000001';
    $this->withToken(str_repeat('a', 64));
    $this->authorityRevoked = false;
    $authority = Mockery::mock(PlanningInputAuthority::class);
    $authority->shouldReceive('check')->andReturnUsing(function (): array {
        abort_if($this->authorityRevoked, 403);

        return ['actor_id' => $this->id];
    });
    $this->app->instance(PlanningInputAuthority::class, $authority);
    $this->body = ['action' => 'plan.read', 'scope' => ['site_id' => $this->id, 'environment' => $this->id, 'resource_id' => $this->id], 'qualification_scope' => ['tenant_id' => $this->id, 'site_id' => $this->id, 'endpoint_id' => $this->id, 'native_scope' => 'fixture', 'installed_tuple' => ['api' => 1], 'action' => 'application.provision', 'method' => 'native_api', 'profile_digest' => str_repeat('a', 64), 'artifacts' => array_fill_keys(['compiler', 'adapter', 'automation', 'contracts'], str_repeat('b', 64))]];
    $this->path = '/v1/tenants/'.$this->id.'/planning-qualification-v2';
});

it('binds current queries to their command identity while rechecking effective authority on every retry', function (): void {
    config(['planning.qualification_registry_file' => null]);
    $key = bin2hex(random_bytes(32));
    $this->withHeader('Idempotency-Key', $key);
    $this->postJson($this->path, $this->body)->assertOk();
    $this->postJson($this->path, $this->body)->assertOk();
    expect(DB::table('app.qualification_command_keys')->count())->toBe(1);
    $changed = $this->body;
    $changed['qualification_scope']['installed_tuple']['api'] = 2;
    $this->postJson($this->path, $changed)->assertStatus(409);
    $this->authorityRevoked = true;
    $this->postJson($this->path, $this->body)->assertForbidden();
    expect(DB::table('app.qualification_command_keys')->count())->toBe(1);
});

it('requires a strong key and rejects expired query identities without replaying support', function (): void {
    config(['planning.qualification_registry_file' => null]);
    $this->withHeader('Idempotency-Key', '')->postJson($this->path, $this->body)->assertUnprocessable();
    $key = bin2hex(random_bytes(32));
    $this->withHeader('Idempotency-Key', $key)->postJson($this->path, $this->body)->assertOk();
    DB::table('app.qualification_command_keys')->update(['expires_at' => now()->subSecond()->getTimestamp()]);
    $this->postJson($this->path, $this->body)->assertStatus(409);
    $this->withHeader('Idempotency-Key', bin2hex(random_bytes(32)))->postJson($this->path, $this->body)->assertOk();
});

it('returns explicit unknown when Assurance has no qualification registry', function (): void {
    config(['planning.qualification_registry_file' => null]);
    $this->postJson($this->path, $this->body)->assertOk()->assertJsonPath('status', 'unknown')->assertJsonPath('expires_at', 0)->assertJsonPath('evidence_level', null)->assertHeader('Cache-Control', 'no-store, private');
});

it('rejects malformed qualification values before returning or retaining a wire response', function (string $fault): void {
    $body = $this->body;
    match ($fault) {
        'missing-endpoint' => $body['qualification_scope']['endpoint_id'] = null,
        'endpoint' => $body['qualification_scope']['endpoint_id'] = 'forged',
        'tuple' => $body['qualification_scope']['installed_tuple'] = [],
        'action' => $body['qualification_scope']['action'] = 'invented',
        'digest' => $body['qualification_scope']['profile_digest'] = 'unverified',
        'artifacts' => $body['qualification_scope']['artifacts'] = ['adapter' => str_repeat('a', 64)],
        'native-scope' => $body['qualification_scope']['native_scope'] = true,
    };
    $this->postJson($this->path, $body)->assertUnprocessable()->assertJsonPath('retryable', false);
    expect(DB::table('app.qualification_command_keys')->count())->toBe(0);
})->with(['missing-endpoint', 'endpoint', 'tuple', 'action', 'digest', 'artifacts', 'native-scope']);

it('does not read a dossier for a mismatched tenant or site', function (): void {
    $body = $this->body;
    $body['qualification_scope']['tenant_id'] = '10000000-0000-4000-8000-000000000002';
    $this->postJson($this->path, $body)->assertForbidden();
});

it('keeps exact tuple values typed and fails closed on ambiguous custody records', function (): void {
    $file = tempnam(sys_get_temp_dir(), 'p05-dossier-');
    config(['planning.qualification_registry_file' => $file]);
    $record = ['scope' => $this->body['qualification_scope'], 'status' => 'qualified'];
    try {
        // Retired V1 wire records cannot be silently treated as unknown.
        file_put_contents($file, json_encode(['schema_version' => 1, 'records' => [$record]], JSON_THROW_ON_ERROR));
        $this->postJson($this->path, $this->body)->assertStatus(503);
        $current = ['record' => $record];
        file_put_contents($file, json_encode(['schema_version' => 2, 'records' => [$current]], JSON_THROW_ON_ERROR));
        $body = $this->body;
        $body['qualification_scope']['installed_tuple']['api'] = true;
        $this->withHeader('Idempotency-Key', bin2hex(random_bytes(32)));
        $this->postJson($this->path, $body)->assertOk()->assertJsonPath('status', 'unknown');
        // Exact-scope but unsigned V2 records require trust; never qualify.
        $this->withHeader('Idempotency-Key', bin2hex(random_bytes(32)))->postJson($this->path, $this->body)->assertStatus(503);
        file_put_contents($file, json_encode(['schema_version' => 2, 'records' => [$current, $current]], JSON_THROW_ON_ERROR));
        $this->postJson($this->path, $this->body)->assertStatus(503);
        file_put_contents($file, '{broken');
        $this->postJson($this->path, $this->body)->assertStatus(503);
    } finally {
        unlink($file);
    }
});

it('rejects malformed current dossiers without interpreting partial or historical records', function (): void {
    $file = tempnam(sys_get_temp_dir(), 'p05-invalid-v2-');
    config(['planning.qualification_registry_file' => $file]);
    try {
        foreach ([
            ['schema_version' => 1, 'records' => []],
            ['schema_version' => 2, 'records' => ['non-list' => []]],
            ['schema_version' => 2, 'records' => ['invalid']],
            ['schema_version' => 2, 'records' => [['record' => ['scope' => 'untyped']]]],
        ] as $invalid) {
            file_put_contents($file, json_encode($invalid, JSON_THROW_ON_ERROR));
            $this->postJson($this->path, $this->body)->assertStatus(503);
        }
    } finally {
        unlink($file);
    }
});

it('rejects qualification registries with unsafe custody or excessive bytes', function (string $fault): void {
    $file = tempnam(sys_get_temp_dir(), 'p05-custody-');
    $link = $file.'-link';
    $record = ['scope' => $this->body['qualification_scope'], 'status' => 'qualified'];
    file_put_contents($file, json_encode(['schema_version' => 1, 'records' => [$record]], JSON_THROW_ON_ERROR));
    config(['planning.qualification_registry_file' => $file]);
    try {
        if ($fault === 'writable') {
            chmod($file, 0666);
        } elseif ($fault === 'symlink') {
            symlink($file, $link);
            config(['planning.qualification_registry_file' => $link]);
        } else {
            file_put_contents($file, str_repeat(' ', 524289));
        }
        $this->postJson($this->path, $this->body)->assertStatus(503);
    } finally {
        if (is_link($link)) {
            unlink($link);
        }
        unlink($file);
    }
})->with(['writable', 'symlink', 'oversized']);

it('does not expose the retired unversioned qualification alias', function (): void {
    $legacy = '/v1/tenants/'.$this->id.'/planning-qualification';
    $this->postJson($legacy, $this->body)->assertNotFound();
});
