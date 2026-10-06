<?php

declare(strict_types=1);

namespace App\Domain\IntentRevisions\Models;

use Illuminate\Database\Eloquent\Model;

final class IntentRevision extends Model
{
    protected $table = 'app.catalogue_revisions';

    protected $keyType = 'string';

    public $incrementing = false;

    public $timestamps = false;

    protected $guarded = ['*'];
}
