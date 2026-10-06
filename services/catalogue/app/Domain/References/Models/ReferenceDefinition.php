<?php

declare(strict_types=1);

namespace App\Domain\References\Models;

use Illuminate\Database\Eloquent\Model;

final class ReferenceDefinition extends Model
{
    protected $table = 'app.catalogue_references';

    protected $keyType = 'string';

    public $incrementing = false;

    public $timestamps = false;

    protected $guarded = ['*'];
}
