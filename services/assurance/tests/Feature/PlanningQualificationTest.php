<?php

declare(strict_types=1);

use App\Application\Planning\Contracts\PlanningInputAuthority;

beforeEach(function (): void {
    $this->id = '10000000-0000-4000-8000-000000000001';
    $authority = Mockery::mock(PlanningInputAuthority::class);
    $authority->shouldReceive('check')->andReturn([]);
    $this->app->instance(PlanningInputAuthority::class, $authority);
    $this->body = ['action' => 'plan.read', 'scope' => ['site_id' => $this->id, 'environment' => $this->id, 'resource_id' => $this->id], 'qualification_scope' => ['tenant_id' => $this->id, 'site_id' => $this->id, 'endpoint_id' => $this->id, 'native_scope' => 'fixture', 'installed_tuple' => ['api' => 1], 'action' => 'application.provision', 'method' => 'native_api', 'profile_digest' => str_repeat('a', 64), 'artifacts' => []]];
    $this->path = '/v1/tenants/'.$this->id.'/planning-qualification';
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
        file_put_contents($file, json_encode(['schema_version' => 1, 'records' => [$record]], JSON_THROW_ON_ERROR));
        $body = $this->body;
        $body['qualification_scope']['installed_tuple']['api'] = true;
        $this->postJson($this->path, $body)->assertOk()->assertJsonPath('status', 'unknown');
        $this->postJson($this->path, $this->body)->assertOk()->assertJsonPath('status', 'qualified');
        file_put_contents($file, json_encode(['schema_version' => 1, 'records' => [$record, $record]], JSON_THROW_ON_ERROR));
        $this->postJson($this->path, $this->body)->assertStatus(503);
        file_put_contents($file, '{broken');
        $this->postJson($this->path, $this->body)->assertStatus(503);
    } finally {
        unlink($file);
    }
});
