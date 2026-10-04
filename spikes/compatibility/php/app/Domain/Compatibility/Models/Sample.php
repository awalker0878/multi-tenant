<?php

declare(strict_types=1);

namespace App\Domain\Compatibility\Models;

use App\Domain\Compatibility\Exceptions\InvalidSampleTransition;
use Illuminate\Database\Eloquent\Model;

/**
 * @property int $id
 * @property string $tenant_id
 * @property string $status
 * @property int $revision
 */
final class Sample extends Model
{
    protected $table = 'compatibility_samples';

    public $timestamps = false;

    /** @var list<string> */
    protected $fillable = ['tenant_id', 'status', 'revision'];

    /** @return array<string, string> */
    protected function casts(): array
    {
        return ['id' => 'integer', 'revision' => 'integer'];
    }

    public function approve(int $expectedRevision): void
    {
        if ($this->status !== 'pending' || $this->revision !== $expectedRevision) {
            throw new InvalidSampleTransition('Sample state or revision does not allow approval.');
        }

        $this->status = 'approved';
        $this->revision++;
    }
}
