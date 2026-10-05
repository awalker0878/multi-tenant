<?php

declare(strict_types=1);

namespace App\Domain\Identity;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Support\Carbon;

/**
 * @property int $id
 * @property string $state
 * @property string|null $password_hash
 * @property int $credential_version
 * @property int $failed_attempts
 * @property Carbon|null $locked_until
 */
final class BootstrapAdministrator extends Model
{
    protected $table = 'app.bootstrap_administrator';

    public $timestamps = false;

    protected $guarded = ['id'];

    protected $hidden = ['password_hash'];

    /** @return array<string, string> */
    protected function casts(): array
    {
        return [
            'credential_version' => 'integer', 'failed_attempts' => 'integer',
            'locked_until' => 'datetime', 'initialized_at' => 'datetime',
            'password_changed_at' => 'datetime', 'retired_at' => 'datetime',
        ];
    }

    public function allowsLocalLogin(): bool
    {
        return in_array($this->state, ['password_change_required', 'local_setup'], true);
    }
}
