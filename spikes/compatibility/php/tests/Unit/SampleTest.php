<?php

declare(strict_types=1);

use App\Domain\Compatibility\Exceptions\InvalidSampleTransition;
use App\Domain\Compatibility\Models\Sample;

it('rejects invalid state and stale revision before changing attributes', function (): void {
    $sample = new Sample(['tenant_id' => 'tenant-a', 'status' => 'pending', 'revision' => 3]);

    expect(fn () => $sample->approve(2))->toThrow(InvalidSampleTransition::class);
    expect($sample->status)->toBe('pending')->and($sample->revision)->toBe(3);

    $sample->approve(3);

    expect($sample->status)->toBe('approved')->and($sample->revision)->toBe(4);
    expect(fn () => $sample->approve(4))->toThrow(InvalidSampleTransition::class);
    expect($sample->revision)->toBe(4);
});
