<?php

declare(strict_types=1);

namespace App\Domain\Compatibility\Models;

use Illuminate\Foundation\Auth\User as Authenticatable;

/**
 * Synthetic test actor; this spike implements no login or identity authority.
 *
 * @property int $id
 * @property string $tenant_id
 * @property string $role
 */
final class Actor extends Authenticatable
{
    /** @var list<string> */
    protected $fillable = ['id', 'tenant_id', 'role'];

    /** @return array<string, string> */
    protected function casts(): array
    {
        return ['id' => 'integer'];
    }
}
