<?php

declare(strict_types=1);

namespace App\Http\Resources;

use App\Domain\Compatibility\Models\Sample;
use Illuminate\Http\Request;
use Illuminate\Http\Resources\Json\JsonResource;

/** @mixin Sample */
final class SampleResource extends JsonResource
{
    /** @return array{id: int, status: string, revision: int} */
    public function toArray(Request $request): array
    {
        return ['id' => $this->id, 'status' => $this->status, 'revision' => $this->revision];
    }
}
