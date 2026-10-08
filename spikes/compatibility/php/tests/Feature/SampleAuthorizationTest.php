<?php

declare(strict_types=1);

use App\Application\Compatibility\Actions\ApproveSample;
use App\Domain\Compatibility\Models\Sample;
use Illuminate\Auth\Access\AuthorizationException;
use Illuminate\Database\QueryException;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Gate;

it('requires authentication for sample reads and writes', function (): void {
    $sample = $this->sample();

    $this->getJson('/samples')->assertUnauthorized();
    $this->postJson('/samples/'.$sample->id.'/approve', ['expected_revision' => 1])->assertUnauthorized();
    $this->assertDatabaseCount('compatibility_audits', 0);
});

it('returns only the actor tenant and explicitly presented fields', function (): void {
    $own = $this->sample();
    $other = $this->sample('tenant-b');

    $this->actingAs($this->actor())->get('/samples', ['X-Inertia' => 'true', 'X-Inertia-Version' => 'p00-compatibility-v1'])
        ->assertOk()
        ->assertJsonCount(1, 'props.samples')
        ->assertJsonPath('props.samples.0.id', $own->id)
        ->assertJsonMissingPath('props.samples.0.tenant_id');

    $this->actingAs($this->actor('tenant-b'))->get('/samples', ['X-Inertia' => 'true', 'X-Inertia-Version' => 'p00-compatibility-v1'])
        ->assertOk()
        ->assertJsonCount(1, 'props.samples')
        ->assertJsonPath('props.samples.0.id', $other->id);
});

it('rejects denied readers and malformed commands without writes', function (): void {
    $sample = $this->sample();

    $this->actingAs($this->actor(role: 'none'))->getJson('/samples')->assertForbidden();
    $this->actingAs($this->actor(role: 'reader'))
        ->postJson('/samples/'.$sample->id.'/approve', ['expected_revision' => 1])->assertForbidden();
    $this->actingAs($this->actor())
        ->postJson('/samples/'.$sample->id.'/approve', ['expected_revision' => 0])->assertUnprocessable()->assertJsonValidationErrors('expected_revision');

    $this->assertDatabaseHas('compatibility_samples', ['id' => $sample->id, 'status' => 'pending', 'revision' => 1]);
    $this->assertDatabaseCount('compatibility_audits', 0);
});

it('does not reveal or mutate another tenant sample', function (): void {
    $sample = $this->sample('tenant-b');

    $this->actingAs($this->actor())->postJson('/samples/'.$sample->id.'/approve', ['expected_revision' => 1])->assertNotFound();

    expect(Gate::forUser($this->actor())->allows('approve', $sample))->toBeFalse();
    $this->assertDatabaseHas('compatibility_samples', ['id' => $sample->id, 'status' => 'pending', 'revision' => 1]);
    $this->assertDatabaseCount('compatibility_audits', 0);
});

it('authorizes the explicit actor when the Action is called without HTTP', function (): void {
    $sample = $this->sample();

    expect(fn () => app(ApproveSample::class)->handle($this->actor(role: 'reader'), $sample->id, 1))
        ->toThrow(AuthorizationException::class);

    $this->assertDatabaseCount('compatibility_audits', 0);
    $this->assertDatabaseHas('compatibility_samples', ['id' => $sample->id, 'status' => 'pending']);
});

it('commits the authorized transition and its local audit together', function (): void {
    $sample = $this->sample();

    $this->actingAs($this->actor())->postJson('/samples/'.$sample->id.'/approve', ['expected_revision' => 1])->assertRedirect('/samples');

    $this->assertDatabaseHas('compatibility_samples', ['id' => $sample->id, 'status' => 'approved', 'revision' => 2]);
    $this->assertDatabaseHas('compatibility_audits', ['sample_id' => $sample->id, 'revision' => 2, 'actor_id' => 100]);
});

it('rejects stale and repeated transitions without adding an audit', function (): void {
    $sample = $this->sample();
    $this->actingAs($this->actor());

    $this->postJson('/samples/'.$sample->id.'/approve', ['expected_revision' => 2])->assertConflict();
    $this->assertDatabaseHas('compatibility_samples', ['id' => $sample->id, 'status' => 'pending', 'revision' => 1]);
    $this->assertDatabaseCount('compatibility_audits', 0);

    $this->postJson('/samples/'.$sample->id.'/approve', ['expected_revision' => 1])->assertRedirect('/samples');
    $this->postJson('/samples/'.$sample->id.'/approve', ['expected_revision' => 2])->assertConflict();
    $this->assertDatabaseCount('compatibility_audits', 1);
});

it('rolls back the first write when the second local write fails', function (): void {
    $sample = $this->sample();
    DB::table('compatibility_audits')->insert(['sample_id' => $sample->id, 'revision' => 2, 'actor_id' => 999]);

    expect(fn () => app(ApproveSample::class)->handle($this->actor(), $sample->id, 1))->toThrow(QueryException::class);

    $this->assertDatabaseHas('compatibility_samples', ['id' => $sample->id, 'status' => 'pending', 'revision' => 1]);
    $this->assertDatabaseCount('compatibility_audits', 1);
    expect(Sample::query()->findOrFail($sample->id)->revision)->toBe(1);
});
