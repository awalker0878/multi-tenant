<?php

declare(strict_types=1);

use App\Application\Messaging\Actions\PublishGovernanceEvent;
use App\Application\Messaging\Contracts\ConfirmedPublisher;
use App\Infrastructure\Messaging\GovernanceEventEncoder;
use Illuminate\Support\Facades\DB;
use PhpAmqpLib\Connection\AMQPConnectionConfig;
use PhpAmqpLib\Connection\AMQPConnectionFactory;
use Symfony\Component\Process\Process;

beforeEach(function (): void {
    if (getenv('P02_TEST_BROKER') !== '1') {
        $this->markTestSkipped('Real TLS broker campaign only.');
    }
    initializeFederationFixture($this);
    $this->tenant = tenantCommand($this, '/v1/tenants', ['name' => 'Synthetic broker tenant', 'administrator_subject' => 'immutable-admin-subject'])->assertCreated()->json('id');
    $config = new AMQPConnectionConfig;
    $config->setHost('127.0.0.1');
    $config->setPort((int) getenv('GOVERNANCE_BROKER_PORT'));
    $config->setUser('p02-observer');
    $config->setPassword(trim(file_get_contents(getenv('P02_OBSERVER_PASSWORD_FILE'))));
    $config->setVhost('product');
    $config->setIsSecure(true);
    $config->setSslCaCert(getenv('GOVERNANCE_BROKER_CA_FILE'));
    $config->setSslVerify(true);
    $config->setSslVerifyName(true);
    $config->setReadTimeout(5.0);
    $config->setHeartbeat(0);
    $this->broker = AMQPConnectionFactory::create($config);
    $this->channel = $this->broker->channel();
    // Drain only this disposable campaign's witness queue.
    while (($message = $this->channel->basic_get('p02.governance')) !== null) {
        $message->ack();
    }
    $this->databasePasswordFile = tempnam(sys_get_temp_dir(), 'p02-broker-password-');
    file_put_contents($this->databasePasswordFile, (string) getenv('P02_TEST_PASSWORD'));
    $this->process = function (string $mode = 'publish'): Process {
        $process = new Process([PHP_BINARY, '-c', php_ini_loaded_file(), base_path('../../scripts/p02/event_process.php'), $mode], base_path(), [
            'DB_HOST' => '127.0.0.1', 'DB_PORT' => getenv('P02_TEST_PORT') ?: '5432',
            'DB_DATABASE' => 'p02_identity_test', 'DB_USERNAME' => 'postgres', 'DB_PASSWORD_FILE' => $this->databasePasswordFile,
            'DB_SSLMODE' => 'prefer', 'APP_ENV' => 'testing',
        ]);
        $process->setTimeout(25);

        return $process;
    };
});

afterEach(function (): void {
    if (isset($this->broker)) {
        $this->broker->close();
        unlink($this->credentialFile);
    }
    if (isset($this->databasePasswordFile)) {
        unlink($this->databasePasswordFile);
    }
});

it('recovers a killed confirmed publisher with a stable wire and durable duplicate witness', function (): void {
    $process = ($this->process)('crash');
    $process->run();
    expect($process->getExitCode())->toBe(91)->and(DB::table('app.governance_outbox')->value('published_at'))->toBeNull();
    $first = $this->channel->basic_get('p02.governance');
    expect($first)->not->toBeNull();
    $wire = $first->getBody();
    $first->ack();
    expect(app(PublishGovernanceEvent::class)->handle())->toBe('published');
    $second = $this->channel->basic_get('p02.governance');
    expect($second)->not->toBeNull()->and($second->getBody())->toBe($wire);
    $second->ack();
    // Explicit synthetic consumer: record identical delivered facts, never grant authority.
    DB::statement('CREATE TABLE app.synthetic_event_inbox (id uuid PRIMARY KEY, wire_hash char(64) NOT NULL)');
    foreach ([$wire, $second->getBody()] as $body) {
        DB::table('app.synthetic_event_inbox')->insertOrIgnore(['id' => json_decode($body, true)['event_id'], 'wire_hash' => hash('sha256', $body)]);
    }
    expect(DB::table('app.synthetic_event_inbox')->count())->toBe(1);
});

it('skips a locked claim then permits two independent relays to finish one remaining event', function (): void {
    DB::beginTransaction();
    DB::table('app.governance_outbox')->lockForUpdate()->first();
    $blocked = ($this->process)();
    $blocked->run();
    expect($blocked->getExitCode())->toBe(0)->and(trim($blocked->getOutput()))->toBe('idle');
    DB::rollBack();
    $one = ($this->process)();
    $two = ($this->process)();
    $one->start();
    $two->start();
    $one->wait();
    $two->wait();
    $results = [trim($one->getOutput()), trim($two->getOutput())];
    sort($results);
    expect($one->getExitCode())->toBe(0)->and($two->getExitCode())->toBe(0)->and($results)->toBe(['idle', 'published']);
    $message = $this->channel->basic_get('p02.governance');
    expect($message)->not->toBeNull();
    $message->ack();
    expect($this->channel->basic_get('p02.governance'))->toBeNull();
});

it('requires a routed confirmation and verified TLS, then recovers after trust is restored', function (): void {
    $row = DB::table('app.governance_outbox')->first();
    $wire = (new GovernanceEventEncoder)->encode($row);
    $publisher = app(ConfirmedPublisher::class);
    expect(fn () => $publisher->publish($wire, $row->id, 'unbound.route'))->toThrow(RuntimeException::class);
    $ca = config('messaging.ca_file');
    config(['messaging.ca_file' => getenv('P02_UNTRUSTED_CA_FILE')]);
    expect(app(PublishGovernanceEvent::class)->handle())->toBe('retry')
        ->and(DB::table('app.governance_outbox')->value('published_at'))->toBeNull();
    config(['messaging.ca_file' => $ca]);
    DB::table('app.governance_outbox')->update(['available_at' => now()]);
    expect(app(PublishGovernanceEvent::class)->handle())->toBe('published');
    $message = $this->channel->basic_get('p02.governance');
    expect($message)->not->toBeNull();
    $message->ack();
});
