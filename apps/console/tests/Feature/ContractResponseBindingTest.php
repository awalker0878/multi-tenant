<?php

declare(strict_types=1);

use App\Domain\Catalogue\CatalogueFailure;
use App\Domain\Inventory\InventoryFailure;
use App\Infrastructure\Catalogue\CatalogueClient;
use App\Infrastructure\Inventory\InventoryClient;
use Illuminate\Support\Facades\Http;

beforeEach(function (): void {
    $this->contractSecret = tempnam(sys_get_temp_dir(), 'contract-bind-');
    file_put_contents($this->contractSecret, str_repeat('c', 64));
    config(['identity.governance_url' => 'https://governance.example.test', 'identity.credential_file' => $this->contractSecret,
        'catalogue.url' => 'https://catalogue.example.test', 'catalogue.credential_file' => $this->contractSecret, 'catalogue.ca_file' => $this->contractSecret,
        'inventory.url' => 'https://inventory.example.test', 'inventory.credential_file' => $this->contractSecret, 'inventory.ca_file' => $this->contractSecret]);
    Http::preventStrayRequests();
});

afterEach(function (): void {
    unlink($this->contractSecret);
});

it('rejects a schema valid response for another requested record or scope', function (array $case, array $value, array $intent): void {
    $poisoned = $value;
    data_set($poisoned, $case['field'], $case['poison']);
    $family = $case['family'];
    Http::fake(['governance.example.test/*' => Http::response(['delegation_token' => str_repeat('d', 64), 'audience' => $family, 'authority_use' => 'request_bound'], 201),
        $family.'.example.test/*' => Http::sequence()->push($value, $case['status'])->push($poisoned, $case['status'])]);
    $client = app($family === 'inventory' ? InventoryClient::class : CatalogueClient::class);
    $invoke = fn () => $family === 'inventory'
        ? $client->call(str_repeat('a', 64), '10000000-0000-4000-8000-000000000001', $case['operation'], $case['parameters'])
        : $client->call(str_repeat('a', 64), '10000000-0000-4000-8000-000000000001', $case['operation'], $case['parameters'], isset($case['include_intent']) ? ['intent' => $intent] : [], null, null, $case['environment']);
    expect($invoke())->toBe($value);
    try {
        $invoke();
        test()->fail('Client accepted another record or scope');
    } catch (CatalogueFailure|InventoryFailure $failure) {
        expect($failure->status)->toBe(403)->and($failure->reason)->toBe('scope_mismatch');
    }
})->with(function (): array {
    $fixtures = json_decode(file_get_contents(__DIR__.'/../Fixtures/contract-response-bindings.json'), true, 512, JSON_THROW_ON_ERROR);
    $cases = [];
    foreach ($fixtures['cases'] as $name => $case) {
        $response = $fixtures['responses'][$case['response']];
        if (isset($response['include_intent'])) {
            unset($response['include_intent']);
            $response['intent'] = $fixtures['intent'];
        }
        $cases[$name] = [$case, $response, $fixtures['intent']];
    }

    return $cases;
});

it('rejects missing extra reserved or invalid path parameters before requesting authority', function (string $family, array $parameters, string $reason): void {
    Http::fake();
    $client = app($family === 'inventory' ? InventoryClient::class : CatalogueClient::class);
    try {
        $client->call(str_repeat('a', 64), '10000000-0000-4000-8000-000000000001', $family === 'inventory' ? 'listEndpoints' : 'getApplication', $parameters);
        test()->fail('Client accepted invalid path parameters');
    } catch (CatalogueFailure|InventoryFailure $failure) {
        expect($failure->status)->toBe(422)->and($failure->reason)->toBe($reason);
    }
    Http::assertNothingSent();
})->with(function (): array {
    $cases = [];
    foreach (['inventory' => 'site', 'catalogue' => 'application'] as $family => $required) {
        foreach (['missing' => [[], 'missing_identity'],
            'extra' => [[$required => '10000000-0000-4000-8000-000000000001', 'extra' => '10000000-0000-4000-8000-000000000001'], 'unexpected_identity'],
            'tenant override' => [[$required => '10000000-0000-4000-8000-000000000001', 'tenant' => '20000000-0000-4000-8000-000000000002'], 'unexpected_identity'],
            'invalid' => [[$required => ['not-a-string']], 'invalid_identity']] as $name => [$parameters, $reason]) {
            $cases[$family.':'.$name] = [$family, $parameters, $reason];
        }
    }

    return $cases;
});

it('bounds Catalogue responses and fails closed for invalid JSON', function (string $raw): void {
    Http::fake(['governance.example.test/*' => Http::response(['delegation_token' => str_repeat('d', 64), 'audience' => 'catalogue', 'authority_use' => 'request_bound'], 201),
        'catalogue.example.test/*' => Http::response($raw, 200)]);
    expect(fn () => app(CatalogueClient::class)->call(str_repeat('a', 64), '10000000-0000-4000-8000-000000000001', 'listApplications'))->toThrow(CatalogueFailure::class);
})->with(['oversize' => fn () => str_repeat(' ', 310001), 'invalid JSON' => '{']);
