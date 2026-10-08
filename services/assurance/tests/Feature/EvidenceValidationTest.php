<?php

declare(strict_types=1);

use App\Application\Evidence\Contracts\EvidenceAuthority;

it('rejects malformed evidence without opening custody or leaking decoder errors', function (string $raw): void {
    $authority = Mockery::mock(EvidenceAuthority::class);
    $authority->shouldReceive('producer')->once();
    $this->app->instance(EvidenceAuthority::class, $authority);

    $this->postJson('/v1/tenants/10000000-0000-4000-8000-000000000001/evidence-uploads', [
        'job_id' => '10000000-0000-4000-8000-000000000002',
        'plan_digest' => str_repeat('a', 64),
        'source_revision' => str_repeat('b', 40),
        'digest' => hash('sha256', $raw),
        'evidence_level' => 'E2',
        'content_base64' => base64_encode($raw),
    ])->assertUnprocessable()->assertJsonPath('message', 'invalid_observation');
})->with([
    'malformed JSON' => '{broken',
    'invalid UTF-8' => "[\"\xff\"]",
    'excessive nesting' => str_repeat('[', 40).'0'.str_repeat(']', 40),
]);
