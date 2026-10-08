<?php

declare(strict_types=1);

beforeEach(function (): void {
    $this->tenant = '10000000-0000-4000-8000-000000000001';
    $this->url = '/internal/tenants/'.$this->tenant.'/qualification-publications';
    $this->payload = [
        'operation' => 'suspend',
        'command_id' => '10000000-0000-4000-8000-000000000002',
        'expected_epoch' => 1,
        'reason' => 'latest native observer contradiction',
        'qualification_scope' => [
            'tenant_id' => $this->tenant,
            'site_id' => '10000000-0000-4000-8000-000000000003',
            'endpoint_id' => '10000000-0000-4000-8000-000000000004',
            'native_scope' => 'project:fixture',
            'installed_tuple' => ['platform' => 'openstack'],
            'action' => 'application.provision',
            'method' => 'native_api',
            'profile_digest' => str_repeat('a', 64),
            'artifacts' => ['adapter' => str_repeat('b', 64)],
        ],
    ];
});

it('does not expose a writable qualification authority without an explicitly commissioned database mode', function (): void {
    config(['planning.qualification_authority_mode' => 'mounted']);
    $this->postJson($this->url, $this->payload)->assertStatus(503);
});

it('refuses to publish when independent reviewer and observer authorities are not enrolled', function (): void {
    config([
        'planning.qualification_authority_mode' => 'database',
        'planning.qualification_reviewer_credential_file' => null,
        'planning.qualification_observer_credential_file' => null,
    ]);
    $this->postJson($this->url, $this->payload)->assertStatus(503);
});

it('refuses publication without correct separate observer authorization', function (): void {
    $reviewer = tempnam(sys_get_temp_dir(), 'assurance-reviewer-');
    $observer = tempnam(sys_get_temp_dir(), 'assurance-observer-');
    $planning = tempnam(sys_get_temp_dir(), 'assurance-planning-');
    try {
        file_put_contents($reviewer, str_repeat('r', 64));
        file_put_contents($observer, str_repeat('o', 64));
        file_put_contents($planning, str_repeat('p', 64));
        config([
            'planning.qualification_authority_mode' => 'database',
            'planning.qualification_reviewer_credential_file' => $reviewer,
            'planning.qualification_observer_credential_file' => $observer,
            'planning.credential_file' => $planning,
        ]);
        $this->withHeaders(['Authorization' => 'Bearer '.str_repeat('r', 64)])
            ->postJson($this->url, $this->payload)->assertForbidden();
        $this->withHeaders(['Authorization' => 'Bearer '.str_repeat('p', 64)])
            ->postJson($this->url, $this->payload)->assertForbidden();
    } finally {
        unlink($reviewer);
        unlink($observer);
        unlink($planning);
    }
});

it('fails closed when observer and reviewer are configured with the same credential', function (): void {
    $file = tempnam(sys_get_temp_dir(), 'assurance-credential-');
    try {
        file_put_contents($file, str_repeat('x', 64));
        config([
            'planning.qualification_authority_mode' => 'database',
            'planning.qualification_reviewer_credential_file' => $file,
            'planning.qualification_observer_credential_file' => $file,
        ]);
        $this->withHeaders(['Authorization' => 'Bearer '.str_repeat('x', 64)])
            ->postJson($this->url, $this->payload)->assertStatus(503);
    } finally {
        unlink($file);
    }
});

it('rejects publication outside the current tenant and invalid typed epochs', function (): void {
    config(['planning.qualification_authority_mode' => 'database']);
    $outside = $this->payload;
    $outside['qualification_scope']['tenant_id'] = '10000000-0000-4000-8000-000000000099';
    $this->postJson($this->url, $outside)->assertForbidden();

    $invalid = $this->payload;
    $invalid['expected_epoch'] = -1;
    $this->postJson($this->url, $invalid)->assertStatus(422);
});
