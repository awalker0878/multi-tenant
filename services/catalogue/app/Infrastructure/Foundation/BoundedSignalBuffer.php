<?php

declare(strict_types=1);

namespace App\Infrastructure\Foundation;

use App\Application\Foundation\Contracts\SignalBuffer;
use RuntimeException;

final class BoundedSignalBuffer implements SignalBuffer
{
    public const int LIMIT = 65536;

    public function __construct(private readonly string $directory = '/tmp/product-telemetry') {}

    /**
     * @return resource */
    private function open()
    {
        if (! is_dir($this->directory) && ! @mkdir($this->directory, 0700)) {
            throw new RuntimeException('Diagnostic directory unavailable');
        }
        clearstatcache();
        if (is_link($this->directory) || (fileperms($this->directory) & 0777) !== 0700) {
            throw new RuntimeException('Diagnostic directory must be private');
        }
        $path = $this->directory.'/events.jsonl';
        if (is_link($path)) {
            throw new RuntimeException('Invalid diagnostic file');
        }
        $handle = @fopen($path, 'c+b');
        if ($handle === false) {
            throw new RuntimeException('Diagnostic file unavailable');
        }
        @chmod($path, 0600);
        $info = fstat($handle);
        if ($info === false || ($info['mode'] & 0170000) !== 0100000 || $info['nlink'] !== 1) {
            fclose($handle);
            throw new RuntimeException('Invalid diagnostic file');
        }

        return $handle;
    }

    public function append(array $record): string
    {
        $raw = json_encode($record, JSON_UNESCAPED_SLASHES | JSON_THROW_ON_ERROR)."\n";
        if (strlen($raw) > 1024) {
            return 'unavailable';
        }
        try {
            $handle = $this->open();
        } catch (RuntimeException) {
            return 'unavailable';
        }
        try {
            if (! flock($handle, LOCK_EX | LOCK_NB)) {
                return 'contended';
            }
            if (fseek($handle, 0, SEEK_END) !== 0 || ($size = ftell($handle)) === false || $size < 0) {
                return 'unavailable';
            }
            if ($size + strlen($raw) > self::LIMIT) {
                return 'full';
            }
            if (@fwrite($handle, $raw) !== strlen($raw) || ! fflush($handle)) {
                ftruncate($handle, $size);

                return 'unavailable';
            }

            return 'buffered';
        } finally {
            fclose($handle);
        }
    }

    public function snapshot(): string
    {
        $handle = $this->open();
        try {
            if (! flock($handle, LOCK_EX | LOCK_NB)) {
                throw new RuntimeException('Diagnostic buffer contended');
            }
            $raw = stream_get_contents($handle, self::LIMIT + 1);
            if ($raw === false || strlen($raw) > self::LIMIT) {
                throw new RuntimeException('Invalid diagnostic snapshot');
            }

            return $raw;
        } finally {
            fclose($handle);
        }
    }

    public function acknowledge(string $expectedSha256): void
    {
        $handle = $this->open();
        try {
            if (! flock($handle, LOCK_EX | LOCK_NB)) {
                throw new RuntimeException('Diagnostic buffer contended');
            }
            $raw = stream_get_contents($handle, self::LIMIT + 1);
            if ($raw === false || strlen($raw) > self::LIMIT || hash('sha256', $raw) !== $expectedSha256) {
                throw new RuntimeException('Diagnostic snapshot changed');
            }
            if (! ftruncate($handle, 0)) {
                throw new RuntimeException('Diagnostic acknowledgement failed');
            }
        } finally {
            fclose($handle);
        }
    }
}
