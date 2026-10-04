<?php

declare(strict_types=1);

$generated = $argv[1];
$prefix = 'P00\\Infrastructure\\Generated\\';
spl_autoload_register(static function (string $class) use ($generated, $prefix): void {
    if (str_starts_with($class, $prefix)) {
        require $generated.'/lib/'.str_replace('\\', '/', substr($class, strlen($prefix))).'.php';
    }
});
$fixtures = json_decode(file_get_contents($argv[2]), true, flags: JSON_THROW_ON_ERROR);
$wire = array_values(array_filter($fixtures, static fn (array $x): bool => $x['id'] === 'sample-valid'))[0]['value'];
$check = static function (bool $condition, string $message): void {
    if (! $condition) {
        throw new RuntimeException($message);
    }
};
$model = new P00\Infrastructure\Generated\Model\Sample($wire);
$check($model->valid(), 'Valid synthetic model rejected');
$check($model->getRevision() === '9007199254740993', 'Decimal precision lost');
$check(json_decode(json_encode($model, JSON_THROW_ON_ERROR), true, flags: JSON_THROW_ON_ERROR) === $wire, 'Nullable wire round-trip changed');
foreach (['phase' => 'executing', 'schema_version' => 2] as $key => $value) {
    $candidate = new P00\Infrastructure\Generated\Model\Sample(array_replace($wire, [$key => $value]));
    $check(! $candidate->valid(), 'Invalid '.$key.' accepted by model validity check');
}
// The constructor is permissive; explicit valid() is not equivalent to a complete wire validator.
$numeric = new P00\Infrastructure\Generated\Model\Sample(array_replace($wire, ['revision' => 9007199254740993]));
$check(is_int($numeric->getRevision()), 'Update measured PHP type-coercion limitation');
echo json_encode(['status' => 'PASS', 'negative_model_cases' => 2, 'known_gap' => 'constructor accepts numeric revision; validate wire schema before deserialization'], JSON_THROW_ON_ERROR).PHP_EOL;
