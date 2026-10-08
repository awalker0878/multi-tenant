<?php
declare(strict_types=1);

// Fetch only reviewed bytes. APK verifies distribution signatures during the
// subsequent offline install using the official base image's trusted keys.
$group = $argv[1] ?? '';
$destination = '/tmp/service-apks';
$lock = json_decode((string) file_get_contents(__DIR__.'/apk.lock.json'), true, flags: JSON_THROW_ON_ERROR);
if (($lock['schema_version'] ?? null) !== 1 || !in_array($group, ['build', 'runtime', 'composer'], true)
    || !isset($lock['groups'][$group]) || $lock['groups'][$group] === [] || file_exists($destination)) {
    throw new RuntimeException('Invalid APK input scope');
}
mkdir($destination, 0700);
$context = stream_context_create(['http' => ['timeout' => 60, 'follow_location' => 0],
    'ssl' => ['verify_peer' => true, 'verify_peer_name' => true]]);
foreach ($lock['groups'][$group] as $filename) {
    $package = $lock['packages'][$filename] ?? null;
    if (!is_string($filename) || !preg_match('/^[a-zA-Z0-9.+_-]+\.apk$/D', $filename)
        || !is_array($package) || !preg_match('/^[a-f0-9]{64}$/D', $package['sha256'] ?? '')
        || !is_int($package['bytes'] ?? null) || $package['bytes'] < 1 || $package['bytes'] > 268435456
        || !preg_match('~^https://dl-cdn\.alpinelinux\.org/alpine/v3\.24/(main|community)/x86_64/~', $package['url'] ?? '')
        || basename($package['url']) !== $filename) {
        throw new RuntimeException('Invalid APK artifact identity');
    }
    $input = fopen($package['url'], 'rb', false, $context);
    $output = fopen($destination.'/'.$filename, 'xb');
    if ($input === false || $output === false) {
        throw new RuntimeException('APK download unavailable');
    }
    $bytes = stream_copy_to_stream($input, $output, $package['bytes'] + 1);
    fclose($input);
    fclose($output);
    if ($bytes !== $package['bytes'] || !hash_equals($package['sha256'], hash_file('sha256', $destination.'/'.$filename))) {
        throw new RuntimeException('APK artifact bytes differ from lock');
    }
}
