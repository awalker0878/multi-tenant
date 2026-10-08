<?php

declare(strict_types=1);

namespace App\Domain\Identity;

use Illuminate\Database\Eloquent\Model;

/**
 * @property int $revision
 * @property string $issuer
 * @property string $client_id
 * @property string $secret_ref
 * @property string $redirect_uri
 * @property string $administrator_subject
 * @property list<string> $private_networks
 */
final class OidcConnection extends Model
{
    protected $table = 'app.oidc_connections';

    protected $primaryKey = 'revision';

    public $timestamps = false;

    protected $guarded = ['revision'];

    protected $hidden = ['secret_ref'];

    /** @return array<string, string> */
    protected function casts(): array
    {
        return ['revision' => 'integer', 'private_networks' => 'array'];
    }

    /** @return array<string, mixed> */
    public function settings(): array
    {
        return [
            'revision' => $this->revision, 'issuer' => $this->issuer,
            'client_id' => $this->client_id, 'redirect_uri' => $this->redirect_uri,
            'administrator_subject' => $this->administrator_subject,
            'private_networks' => $this->private_networks, 'secret_configured' => true,
        ];
    }
}
