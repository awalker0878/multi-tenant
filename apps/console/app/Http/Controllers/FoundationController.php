<?php

declare(strict_types=1);

namespace App\Http\Controllers;

use Inertia\Inertia;
use Inertia\Response;

final class FoundationController
{
    public function __invoke(): Response
    {
        // Public, explicitly allowlisted presentation data; no service records.
        return Inertia::render('Foundation', [
            'productName' => 'Enterprise Workload Mobility and Secure Hosting',
            'implementationState' => 'foundation',
        ]);
    }
}
