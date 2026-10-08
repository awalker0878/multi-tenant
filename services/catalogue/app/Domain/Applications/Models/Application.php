<?php

declare(strict_types=1);

namespace App\Domain\Applications\Models;

use Illuminate\Database\Eloquent\Model;

/**
 * @property string $id
 * @property string $tenant_id
 * @property string $name
 * @property int $version
 */
final class Application extends Model
{
    protected $table = 'app.catalogue_applications';

    protected $keyType = 'string';

    public $incrementing = false;

    public $timestamps = false;

    protected $guarded = ['*'];
}
