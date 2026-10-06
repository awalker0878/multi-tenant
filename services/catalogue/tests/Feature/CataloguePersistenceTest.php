<?php

declare(strict_types=1);
use App\Application\Authorization\Contracts\ConsoleCaller;
use App\Application\Authorization\Contracts\DelegatedAuthority;
use App\Application\Authorization\Contracts\OwnerDirectory;
use App\Application\Authorization\Data\ActorContext;
use App\Domain\Authorization\AccessDenied;
use Illuminate\Database\QueryException;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Str;

beforeEach(function (): void {
    if (getenv('P03_TEST_POSTGRES') !== '1') {
        $this->markTestSkipped('Requires disposable P03 PostgreSQL integration campaign.');
    }
    config(['database.connections.pgsql.host' => getenv('P03_PGHOST') ?: '127.0.0.1', 'database.connections.pgsql.port' => getenv('P03_PGPORT') ?: '5432', 'database.connections.pgsql.database' => 'p03_catalogue_test', 'database.connections.pgsql.username' => 'catalogue_runtime', 'database.connections.pgsql.password' => getenv('P03_RUNTIME_PASSWORD') ?: '', 'database.connections.pgsql.sslmode' => getenv('P03_SSLMODE') ?: 'verify-full', 'database.connections.pgsql.sslrootcert' => getenv('P03_SSLROOTCERT') ?: null]);
    DB::purge('pgsql');
    $dsn = 'pgsql:host='.(getenv('P03_PGHOST') ?: '127.0.0.1').';port='.(getenv('P03_PGPORT') ?: '5432').';dbname=p03_catalogue_test;sslmode='.(getenv('P03_SSLMODE') ?: 'verify-full').';sslrootcert='.(getenv('P03_SSLROOTCERT') ?: '');
    $this->admin = new PDO($dsn, 'postgres', getenv('P03_ADMIN_PASSWORD') ?: '', [PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION]);
    $this->admin->exec('DROP SCHEMA IF EXISTS app CASCADE; CREATE SCHEMA app AUTHORIZATION catalogue_owner; GRANT USAGE ON SCHEMA app TO catalogue_runtime');
    $migration = file_get_contents(database_path('migrations/002_catalogue.sql'));
    $this->admin->exec(preg_replace('/^\\\\set.*$/m', '', $migration));
    $this->tenant = '00000000-0000-4000-8000-000000000001';
    $this->actor = '00000000-0000-4000-8000-000000000002';
    $this->intent = catalogueIntent();
    $this->denied = false;
    $test = $this;
    $this->app->instance(ConsoleCaller::class, new class implements ConsoleCaller
    {
        public function accepts(string $credential): bool
        {
            return $credential === str_repeat('a', 64);
        }
    });
    $this->app->instance(DelegatedAuthority::class, new class($test) implements DelegatedAuthority
    {
        public function __construct(private object $test) {}

        public function check(string $token, string $tenant, string $action, array $scope): ActorContext
        {
            if ($this->test->denied) {
                throw new AccessDenied;
            }

return new ActorContext($this->test->actor, $tenant, $action, $scope, '00000000-0000-4000-8000-000000000005');
        }
    });
    $this->app->instance(OwnerDirectory::class, new class implements OwnerDirectory
    {
        public function assertOwners(ActorContext $actor, array $owners): void {}
    });
    foreach ([10 => 'environment', 11 => 'wsd', 12 => 'wsd', 21 => 'security-domain', 22 => 'security-domain'] as $i => $kind) {
        $id = sprintf('00000000-0000-4000-8000-%012d', $i);
        $def = ['name' => $kind.$i, 'owner_id' => $this->actor, ...($kind === 'environment' ? [] : ['shareable' => true]), ...($kind === 'security-domain' ? ['zone' => $i === 21 ? 'OZ' : 'RZ'] : [])];
        $q = $this->admin->prepare('INSERT INTO app.catalogue_references(id,tenant_id,kind,name,version) VALUES(?,?,?,?,1)');
        $q->execute([$id, $this->tenant, $kind, $def['name']]);
        $q = $this->admin->prepare('INSERT INTO app.catalogue_reference_versions(tenant_id,reference_id,version,definition,actor_id) VALUES(?,?,1,?,?)');
        $q->execute([$this->tenant, $id, json_encode($def), $this->actor]);
    }
    $this->path = '/v1/tenants/'.$this->tenant.'/applications';
    $this->withToken(str_repeat('a', 64))->withHeader('X-Actor-Delegation', str_repeat('b', 64));
});
afterEach(function (): void {
    DB::disconnect('pgsql');
});
function publishCatalogue(object $t, ?string $app = null, ?string $etag = null, ?string $key = null, ?array $intent = null)
{
    $t->withHeader('Idempotency-Key', $key ?? (string) Str::uuid());
    if ($etag !== null) {
        $t->withHeader('If-Match', $etag);
    }

    return $t->postJson($t->path.($app === null ? '' : '/'.$app.'/intent-revisions'), ['intent' => $intent ?? $t->intent, ...($app === null ? ['name' => 'Permit Desk'] : [])]);
}
it('commits full immutable intent receipt audit event and typed tenant associations in one transaction', function (): void {
    $first = publishCatalogue($this)->assertCreated()->json();
    $this->getJson($this->path.'/'.$first['application_id'].'/intent-revisions/'.$first['revision_id'])->assertOk()->assertJsonPath('intent.workloads.0.requirements.0.strength', 'required')->assertJsonPath('digest', $first['digest']);
    expect(DB::table('app.catalogue_revisions')->count())->toBe(1)->and(DB::table('app.catalogue_commands')->count())->toBe(1)->and(DB::table('app.catalogue_audit')->count())->toBe(1)->and(DB::table('app.catalogue_outbox')->count())->toBe(1)->and(DB::table('app.catalogue_revision_references')->count())->toBe(5);
    $this->getJson($this->path)->assertOk()->assertJsonCount(1, 'applications');
});
it('returns the original receipt after a lost response and later edits while rejecting key payload reuse and stale edits', function (): void {
    $key = (string) Str::uuid();
    $first = publishCatalogue($this, key: $key)->assertCreated()->json();
    $i = $this->intent;
    $i['workloads'][0]['compute']['vcpus'] = 4;
    $second = publishCatalogue($this, $first['application_id'], $first['etag'], intent: $i)->assertCreated()->json();
    publishCatalogue($this, key: $key)->assertCreated()->assertExactJson($first);
    publishCatalogue($this, key: $key, intent: $i)->assertStatus(409);
    publishCatalogue($this, $first['application_id'], $first['etag'], intent: $i)->assertStatus(412);
    $this->getJson($this->path.'/'.$first['application_id'].'/intent-revisions')->assertOk()->assertJsonCount(2, 'revisions');
    $this->getJson($this->path.'/'.$first['application_id'].'/intent-revisions/'.$first['revision_id'])->assertJsonPath('intent.workloads.0.compute.vcpus', 2);
    expect(DB::table('app.catalogue_revisions')->count())->toBe(2)->and($second['sequence'])->toBe(2);
});
it('rejects foreign retired stale shared and wrong-kind references without partial writes', function (string $mode): void {
    match ($mode) {
        'foreign' => $this->intent['workloads'][0]['wsd']['id'] = '00000000-0000-4000-8000-000000000999',
        'kind' => $this->intent['workloads'][0]['wsd'] = $this->intent['environment'],
        'stale' => $this->intent['environment']['version'] = 2,
        'retired' => $this->admin->exec("UPDATE app.catalogue_references SET retired=true WHERE kind='environment'"),
    };
    publishCatalogue($this)->assertStatus(422);
    expect(DB::table('app.catalogue_applications')->count())->toBe(0)->and(DB::table('app.catalogue_revisions')->count())->toBe(0);
})->with(['foreign', 'kind', 'stale', 'retired']);
it('enforces separate reference administration and refuses ZIP immutable identity and in-use retirement', function (): void {
    $base = '/v1/tenants/'.$this->tenant.'/security-domains';
    $key = (string) Str::uuid();
    $this->withHeader('Idempotency-Key', $key)->postJson($base, ['name' => 'ZIP', 'owner_id' => $this->actor, 'shareable' => false, 'zone' => 'ZIP'])->assertStatus(422);
    $ref = $this->withHeader('Idempotency-Key', (string) Str::uuid())->postJson($base, ['name' => 'Restricted', 'owner_id' => $this->actor, 'shareable' => true, 'zone' => 'RZ'])->assertCreated()->json();
    $this->withHeader('Idempotency-Key', (string) Str::uuid())->withHeader('If-Match', $ref['etag'])->putJson($base.'/'.$ref['id'], ['name' => 'Restricted', 'owner_id' => $this->actor, 'shareable' => true, 'zone' => 'OZ'])->assertStatus(409);
    $this->withHeader('Idempotency-Key', (string) Str::uuid())->postJson($base.'/'.$ref['id'].'/retirement')->assertCreated()->assertJsonPath('retired', true);
    publishCatalogue($this)->assertCreated();
    $id = $this->intent['workloads'][0]['security_domain']['id'];
    $this->withHeader('Idempotency-Key', (string) Str::uuid())->withHeader('If-Match', '"'.$id.':1"')->postJson($base.'/'.$id.'/retirement')->assertStatus(409);
});
it('rolls back revision pointer receipt audit and workload bindings when durable outbox persistence fails', function (): void {
    $this->admin->exec('REVOKE INSERT ON app.catalogue_outbox FROM catalogue_runtime');
    publishCatalogue($this)->assertStatus(503);
    foreach (['catalogue_applications', 'catalogue_workloads', 'catalogue_revisions', 'catalogue_commands', 'catalogue_audit'] as $table) {
        expect(DB::table('app.'.$table)->count())->toBe(0);
    }
});
it('denies runtime modification of immutable history even outside Eloquent', function (): void {
    $first = publishCatalogue($this)->assertCreated()->json();
    foreach (['catalogue_revisions', 'catalogue_commands', 'catalogue_audit', 'catalogue_reference_versions', 'catalogue_revision_references'] as $table) {
        try {
            DB::statement('DELETE FROM app.'.$table);
            $this->fail('Immutable delete succeeded');
        } catch (QueryException $e) {
            expect($e->getCode())->toBe('42501');
        }
    }
    expect(DB::table('app.catalogue_revisions')->count())->toBe(1);
});
it('reauthorizes duplicate receipts history and detail after revocation and isolates route tenant', function (): void {
    $key = (string) Str::uuid();
    $first = publishCatalogue($this, key: $key)->assertCreated()->json();
    $this->denied = true;
    publishCatalogue($this, key: $key)->assertForbidden();
    $this->getJson($this->path.'/'.$first['application_id'])->assertForbidden();
    $this->denied = false;
    $this->getJson(str_replace($this->tenant, '00000000-0000-4000-8000-000000000099', $this->path).'/'.$first['application_id'])->assertNotFound();
});
it('never reassigns workloads or deployment identities to another application', function (): void {
    publishCatalogue($this)->assertCreated();
    publishCatalogue($this)->assertStatus(422);
    expect(DB::table('app.catalogue_applications')->count())->toBe(1);
});
it('holds explicit non-shared references across applications', function (): void {
    $this->admin->exec("UPDATE app.catalogue_reference_versions SET definition=jsonb_set(definition,'{shareable}','false') WHERE reference_id='00000000-0000-4000-8000-000000000011'");
    publishCatalogue($this)->assertCreated();
    $i = $this->intent;
    $old = $i['workloads'][0]['id'];
    $new = (string) Str::uuid();
    $i['workloads'][0]['id'] = $new;
    foreach ($i['dependencies'] as &$edge) {
        if ($edge['from'] === $old) {
            $edge['from'] = $new;
        }if ($edge['to'] === $old) {
            $edge['to'] = $new;
        }
    }unset($edge);
    publishCatalogue($this, intent: $i)->assertStatus(422)->assertJsonPath('error', 'reference_sharing_not_authorized');
});
it('bounds representative large tenant pages and rejects foreign cursors', function (): void {
    $statement = $this->admin->prepare('INSERT INTO app.catalogue_applications(id,tenant_id,name,version) VALUES(?,?,?,1)');
    for ($i = 0; $i < 501; $i++) {
        $statement->execute([(string) Str::uuid(), $this->tenant, 'Synthetic '.$i]);
    }
    DB::enableQueryLog();
    $page = $this->getJson($this->path)->assertOk()->assertJsonCount(50, 'applications');
    expect(count(DB::getQueryLog()))->toBe(1);
    $cursor = $page->json('next_cursor');
    expect($cursor)->toBeString();
    $this->getJson($this->path.'?cursor='.urlencode($cursor))->assertOk()->assertJsonCount(50,'applications');
    $this->getJson(str_replace($this->tenant,'00000000-0000-4000-8000-000000000099',$this->path).'?cursor='.urlencode($cursor))->assertStatus(422);
});
