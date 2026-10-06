<?php

declare(strict_types=1);
use App\Domain\IntentRevisions\CanonicalJson;
use App\Domain\IntentRevisions\IntentDocument;
use App\Domain\IntentRevisions\IntentFailure;
use App\Infrastructure\Catalogue\SchemaIntentValidator;

function catalogueIntent(): array
{
    return json_decode(file_get_contents(__DIR__.'/../Fixtures/permit-desk-v1.json'), true, 512, JSON_THROW_ON_ERROR);
}
it('preserves complete multi-domain intent and unsupported mandatory controls through canonical round-trip', function (): void {
    $intent = catalogueIntent();
    (new SchemaIntentValidator)->validate($intent);
    IntentDocument::check($intent);
    expect(json_decode(CanonicalJson::encode($intent), true))->toEqual($intent);
    $reversed = array_reverse($intent, true);
    expect(CanonicalJson::encode($reversed))->toBe(CanonicalJson::encode($intent));
    expect($intent['workloads'][0]['requirements'][0]['strength'])->toBe('required');
});
it('rejects structural, native-credential and placement ambiguity', function (string $case): void {
    $i = catalogueIntent();
    match ($case) {
        'unknown' => $i['password'] = 'do-not-accept', 'native' => $i['workloads'][0]['native_vm_id'] = 'provider-123',
        'fractional' => $i['workloads'][0]['compute']['vcpus'] = 1.5,'empty' => $i['workloads'] = [],
        'missing' => $i['workloads'][0]['guest'] = [], 'huge' => $i['acceptance_criteria'] = [str_repeat('x', 501)],
        'strength' => $i['requirements'] = [['key' => 'security.example', 'strength' => 'best_effort', 'value' => true, 'reason' => 'test']],
    };
    expect(fn () => (new SchemaIntentValidator)->validate($i))->toThrow(IntentFailure::class);
})->with(['unknown', 'native', 'fractional', 'empty', 'missing', 'huge', 'strength']);
it('rejects invalid owned graph associations with a stable actionable field', function (string $case, string $reason): void {
    $i = catalogueIntent();
    match ($case) {
        'cycle' => $i['dependencies'][] = array_replace($i['dependencies'][0], ['from' => $i['workloads'][1]['id'], 'to' => $i['workloads'][0]['id']]),
        'self' => $i['dependencies'][0]['to'] = $i['workloads'][0]['id'],
        'dangling' => $i['dependencies'][0]['to'] = '00000000-0000-4000-8000-000000000999',
        'duplicate' => $i['workloads'][1]['id'] = $i['workloads'][0]['id'],
        'nic' => $i['workloads'][0]['nics'][0]['security_domain_id'] = $i['workloads'][1]['security_domain']['id'],
        'order' => $i['workloads'][0]['disks'][0]['order'] = 1,
        'boot' => $i['workloads'][0]['disks'][0]['boot'] = false,
        'dataset' => $i['workloads'][0]['disks'][0]['dataset_id'] = '00000000-0000-4000-8000-000000000999',
        'interface' => $i['dependencies'][1]['controlled_interface'] = false,
        'port' => $i['dependencies'][1]['port'] = null,
        'service' => $i['services'][0]['workload_id'] = '00000000-0000-4000-8000-000000000999',
    };
    try {
        IntentDocument::check($i);
        $this->fail('Invalid graph accepted');
    } catch (IntentFailure $e) {
        expect($e->reason)->toBe($reason)->and($e->field)->not->toBe('');
    }
})->with([['cycle', 'dependency_cycle'], ['self', 'dangling_or_self_dependency'], ['dangling', 'dangling_or_self_dependency'], ['duplicate', 'duplicate_identity'], ['nic', 'nic_domain_mismatch'], ['order', 'device_order_gap'], ['boot', 'one_boot_disk_required'], ['dataset', 'dangling_dataset'], ['interface', 'controlled_interface_required'], ['port', 'protocol_port_mismatch'], ['service', 'dangling_service_workload']]);
it('permits bidirectional communication while checking startup and shutdown graphs independently', function (): void {
    $i = catalogueIntent();
    $i['dependencies'][] = array_replace($i['dependencies'][1], ['from' => $i['workloads'][1]['id'], 'to' => $i['workloads'][0]['id']]);
    $i['dependencies'][] = array_replace($i['dependencies'][0], ['kind' => 'shutdown', 'from' => $i['workloads'][1]['id'], 'to' => $i['workloads'][0]['id']]);
    IntentDocument::check($i);
    expect(true)->toBeTrue();
});

it('rejects integer values that a browser would silently round', function (int $value): void {
    $intent = catalogueIntent();
    $intent['workloads'][0]['requirements'][0]['value'] = $value;
    (new SchemaIntentValidator)->validate($intent);
    expect(fn () => IntentDocument::check($intent))->toThrow(IntentFailure::class, 'integer_outside_interoperable_range');
})->with([9007199254740992, -9007199254740992]);

it('preserves typed requirement values at the interoperable integer boundary', function (): void {
    $intent = catalogueIntent();
    $intent['workloads'][0]['requirements'][0]['value'] = 9007199254740991;
    IntentDocument::check($intent);
    expect(json_decode(CanonicalJson::encode($intent), true)['workloads'][0]['requirements'][0]['value'])->toBe(9007199254740991);
});
