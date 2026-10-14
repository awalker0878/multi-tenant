<?php

declare(strict_types=1);

use App\Application\Planning\Contracts\PlanningInputAuthority;

beforeEach(function (): void {
    $this->id = '10000000-0000-4000-8000-000000000001';
    $this->withToken(str_repeat('a', 64));
    $authority = Mockery::mock(PlanningInputAuthority::class);
    $authority->shouldReceive('check')->andReturn([]);
    $this->app->instance(PlanningInputAuthority::class, $authority);
    $this->body = ['action' => 'plan.read', 'scope' => ['site_id' => $this->id, 'environment' => $this->id, 'resource_id' => $this->id], 'qualification_scope' => ['tenant_id' => $this->id, 'site_id' => $this->id, 'endpoint_id' => $this->id, 'native_scope' => 'fixture', 'installed_tuple' => ['api' => 1], 'action' => 'application.provision', 'method' => 'native_api', 'profile_digest' => str_repeat('a', 64), 'artifacts' => []]];
    $this->path = '/v1/tenants/'.$this->id.'/planning-qualification-v2';
});

it('returns explicit unknown when Assurance has no qualification registry', function (): void {
    config(['planning.qualification_registry_file' => null]);
    $this->postJson($this->path, $this->body)->assertOk()->assertJsonPath('status', 'unknown')->assertJsonPath('expires_at', 0)->assertJsonPath('evidence_level', null)->assertHeader('Cache-Control', 'no-store, private');
});

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
        $this->postJson($this->path, $body)->assertOk()->assertJsonPath('status', 'unknown');
        // Exact-scope but unsigned V2 records require trust; never qualify.
        $this->postJson($this->path, $this->body)->assertStatus(503);
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
