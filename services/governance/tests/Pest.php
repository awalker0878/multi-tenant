<?php

declare(strict_types=1);

use Tests\TestCase;

pest()->extend(TestCase::class)->afterEach(function (): void {
    if (isset($this->admissionFile) && is_file($this->admissionFile)) {
        unlink($this->admissionFile);
    }
})->in('Feature');

require_once __DIR__.'/Support/IdentityFixture.php';
