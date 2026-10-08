<?php

declare(strict_types=1);

require __DIR__.'/../../services/catalogue/vendor/autoload.php';
$generated = $argv[1];
$prefix = 'P01\\Infrastructure\\Generated\\';
spl_autoload_register(static function (string $class) use ($generated, $prefix): void {
    if (str_starts_with($class, $prefix)) {
        require $generated.'/lib/'.str_replace('\\', '/', substr($class, strlen($prefix))).'.php';
    }
});
$api = json_decode(file_get_contents(__DIR__.'/../../contracts/openapi/foundation-health-v1.json'));
$fixtures = json_decode(file_get_contents(__DIR__.'/health-fixtures.json'));
$validator = new Opis\JsonSchema\Validator;
$results = [];
foreach ($fixtures as $fixture) {
    $schema = $api->components->schemas->{$fixture->schema};
    $valid = $validator->validate($fixture->value, $schema)->isValid();
    if ($valid !== $fixture->valid) {
        throw new RuntimeException('Unexpected fixture verdict: '.$fixture->id);
    }
    if ($valid) {
        $class = $prefix.'Model\\'.$fixture->schema;
        $wire = json_decode(json_encode($fixture->value, JSON_THROW_ON_ERROR), true, flags: JSON_THROW_ON_ERROR);
        $model = new $class($wire);
        if (! $model->valid() || json_decode(json_encode($model, JSON_THROW_ON_ERROR)) != $fixture->value) {
            throw new RuntimeException('Generated model changed valid wire data: '.$fixture->id);
        }
    }
    $results[] = ['id' => $fixture->id, 'valid' => $valid];
}
echo json_encode($results, JSON_THROW_ON_ERROR).PHP_EOL;
