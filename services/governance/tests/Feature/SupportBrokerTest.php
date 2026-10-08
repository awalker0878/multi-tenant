<?php

declare(strict_types=1);

use App\Application\Messaging\Actions\PublishSupportEvent;
use App\Application\Messaging\Contracts\ConfirmedPublisher;
use App\Infrastructure\Messaging\SupportEventEncoder;
use Illuminate\Support\Facades\DB;
use PhpAmqpLib\Connection\AMQPConnectionConfig;
use PhpAmqpLib\Connection\AMQPConnectionFactory;
use PhpAmqpLib\Exception\AMQPProtocolChannelException;
use Symfony\Component\Process\Process;

beforeEach(function (): void {
    if (getenv('P02_TEST_BROKER') !== '1') {
        $this->markTestSkipped('Real TLS broker campaign only.');
    }
    initializeSupportFixture($this);
    DB::table('app.support_outbox')->update(['published_at' => now()]);
    createSupportRequest($this);
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
    $this->brokerConfig = $config;
    $this->broker = AMQPConnectionFactory::create($config);
    $this->channel = $this->broker->channel();
    // Drain only this disposable campaign's witness queue.
    while (($message = $this->channel->basic_get('p02.support')) !== null) {
        $message->ack();
    }
    $this->databasePasswordFile = tempnam(sys_get_temp_dir(), 'p02-broker-password-');
    file_put_contents($this->databasePasswordFile, (string) getenv('P02_TEST_PASSWORD'));
    $this->process = function (string $mode = 'publish'): Process {
        $process = new Process([PHP_BINARY, '-c', php_ini_loaded_file(), base_path('../../scripts/p02/event_process.php'), $mode, 'support'], base_path(), [
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
    expect($process->getExitCode())->toBe(91)->and(DB::table('app.support_outbox')->where('event', 'support.access.requested')->value('published_at'))->toBeNull();
    $first = $this->channel->basic_get('p02.support');
    expect($first)->not->toBeNull();
    $wire = $first->getBody();
    $first->ack();
    expect(app(PublishSupportEvent::class)->handle())->toBe('published');
    $second = $this->channel->basic_get('p02.support');
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
    DB::table('app.support_outbox')->whereNull('published_at')->lockForUpdate()->first();
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
    $message = $this->channel->basic_get('p02.support');
    expect($message)->not->toBeNull();
    $message->ack();
    expect($this->channel->basic_get('p02.support'))->toBeNull()
        ->and($this->channel->basic_get('p02.governance'))->toBeNull()
        ->and($this->channel->basic_get('p02.identity'))->toBeNull();
});

it('requires a routed confirmation and verified TLS, then recovers after trust is restored', function (): void {
    $row = DB::table('app.support_outbox')->whereNull('published_at')->first();
    $wire = (new SupportEventEncoder)->encode($row);
    $publisher = app(ConfirmedPublisher::class);
    expect(fn () => $publisher->publish($wire, $row->id, 'unbound.route'))->toThrow(RuntimeException::class);
    $ca = config('messaging.ca_file');
    config(['messaging.ca_file' => getenv('P02_UNTRUSTED_CA_FILE')]);
    expect(app(PublishSupportEvent::class)->handle())->toBe('retry')
        ->and(DB::table('app.support_outbox')->where('event', 'support.access.requested')->value('published_at'))->toBeNull();
    config(['messaging.ca_file' => $ca]);
    DB::table('app.support_outbox')->update(['available_at' => now()]);
    expect(app(PublishSupportEvent::class)->handle())->toBe('published');
    $message = $this->channel->basic_get('p02.support');
    expect($message)->not->toBeNull();
    $message->ack();
});

it('enforces separate Console and support-audit queue privileges at the real broker', function (): void {
    foreach ([['console', 'P02_CONSOLE_PASSWORD_FILE', 'p02.support'],
        ['support-audit', 'P02_SUPPORT_AUDIT_PASSWORD_FILE', 'p02.identity']] as [$user, $passwordFile, $forbidden]) {
        $config = clone $this->brokerConfig;
        $config->setUser($user);
        $config->setPassword(trim(file_get_contents(getenv($passwordFile))));
        $connection = AMQPConnectionFactory::create($config);
        try {
            try {
                $connection->channel()->basic_get($forbidden);
                test()->fail('Cross-audience queue read must fail');
            } catch (AMQPProtocolChannelException $error) {
                expect($error->getCode())->toBe(403);
            }
            try {
                $connection->channel()->queue_declare('forbidden-support-topology', false, true);
                test()->fail('Consumer must not configure broker topology');
            } catch (AMQPProtocolChannelException $error) {
                expect($error->getCode())->toBe(403);
            }
        } finally {
            $connection->close();
        }
    }
});
