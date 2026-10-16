<?php

declare(strict_types=1);

// Executes the real Laravel route, middleware and database-backed owner.
// No consumer credit: this test does not execute the Console client.
beforeEach(function (): void {
    initializeFederationFixture($this);
    $this->firstTenant = tenantCommand($this, '/v1/tenants', [
        'name' => 'Evidence tenant A',
        'administrator_subject' => 'immutable-admin-subject',
    ])->assertCreated()->json('id');
    $this->secondTenant = tenantCommand($this, '/v1/tenants', [
        'name' => 'Evidence tenant B',
        'administrator_subject' => 'boundary-owner-b',
    ])->assertCreated()->json('id');
});

afterEach(function (): void {
    unlink($this->credentialFile);
    $this->travelBack();
});

it('executes governance tenant-directory and denies a foreign tenant to the same actor', function (): void {
    $this->getJson('/v1/tenant-directory')
        ->assertOk()
        ->assertHeader('Cache-Control', 'no-store, private')
        ->assertJsonPath('tenants.0.id', $this->firstTenant)
        ->assertJsonMissing(['id' => $this->secondTenant]);

    $this->getJson('/v1/tenants/'.$this->firstTenant)
        ->assertOk()
        ->assertJsonPath('tenant.id', $this->firstTenant);
    $this->getJson('/v1/tenants/'.$this->secondTenant)->assertNotFound();
    $this->withHeader('Authorization', 'Bearer invalid')
        ->getJson('/v1/tenant-directory')->assertUnauthorized();
});
