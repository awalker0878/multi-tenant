<?php

declare(strict_types=1);

beforeEach(function (): void {
    $this->id = '10000000-0000-4000-8000-000000000001';
    $this->caller = tempnam(sys_get_temp_dir(), 'migration-caller-');
    $this->outgoing = tempnam(sys_get_temp_dir(), 'migration-outgoing-');
    file_put_contents($this->caller, str_repeat('a', 64));
    file_put_contents($this->outgoing, str_repeat('b', 64));
    config(['planning.credential_file' => $this->caller, 'planning.governance_credential_file' => $this->outgoing, 'planning.migration_support_registry_file' => null]);
    $this->path = '/v1/tenants/'.$this->id.'/migration-qualifications';
    $this->body = ['scope' => ['tenant_id' => $this->id, 'site_id' => $this->id, 'resource_id' => $this->id, 'environment' => $this->id], 'tranche_sha256' => str_repeat('c', 64), 'release_sha256' => str_repeat('d', 64)];
});

afterEach(function (): void {
    unlink($this->caller);
    unlink($this->outgoing);
});

it('requires the service caller and returns no invented native evidence', function (): void {
    $this->postJson($this->path, $this->body)->assertForbidden();
    $this->withToken(str_repeat('a', 64))->postJson($this->path, $this->body)->assertOk()->assertJsonPath('records', [])->assertJsonPath('native_write_authorized', false)->assertHeader('Cache-Control', 'no-store, private');
    $this->postJson($this->path, $this->body + ['records' => []])->assertUnprocessable();
});

it('binds every scope dimension and rejects ambiguous or writable custody', function (): void {
    $file = tempnam(sys_get_temp_dir(), 'migration-registry-');
    config(['planning.migration_support_registry_file' => $file]);
    $this->withToken(str_repeat('a', 64));
    $record = $this->body + ['records' => [['level' => 'E3']]];
    try {
        file_put_contents($file, json_encode(['schema_version' => 1, 'assignments' => [$record]], JSON_THROW_ON_ERROR));
        $this->postJson($this->path, $this->body)->assertOk()->assertJsonPath('records', []);
        $other = $this->body;
        $other['scope']['site_id'] = '10000000-0000-4000-8000-000000000002';
        $this->postJson($this->path, $other)->assertOk()->assertJsonPath('records', []);
        $other['scope']['tenant_id'] = $other['scope']['site_id'];
        $this->postJson($this->path, $other)->assertForbidden();
        file_put_contents($file, json_encode(['schema_version' => 1, 'assignments' => [$record, $record]], JSON_THROW_ON_ERROR));
        $this->postJson($this->path, $this->body)->assertStatus(503);
        chmod($file, 0666);
        $this->postJson($this->path, $this->body)->assertStatus(503);
    } finally {
        unlink($file);
    }
});

it('requires typed migration scope values and accepts reordered keys', function (string $field): void {
    $file = tempnam(sys_get_temp_dir(), 'migration-scope-');
    config(['planning.migration_support_registry_file' => $file]);
    $this->withToken(str_repeat('a', 64));
    $record = $this->body + ['records' => [['level' => 'E3']]];
    try {
        $record['scope'] = array_reverse($record['scope'], true);
        file_put_contents($file, json_encode(['schema_version' => 1, 'assignments' => [$record]], JSON_THROW_ON_ERROR));
        $this->postJson($this->path, $this->body)->assertOk()->assertJsonPath('records', []);
        $record['scope'][$field] = true;
        file_put_contents($file, json_encode(['schema_version' => 1, 'assignments' => [$record]], JSON_THROW_ON_ERROR));
        $this->postJson($this->path, $this->body)->assertOk()->assertJsonPath('records', []);
    } finally {
        unlink($file);
    }
})->with(['tenant_id', 'site_id', 'resource_id', 'environment']);
