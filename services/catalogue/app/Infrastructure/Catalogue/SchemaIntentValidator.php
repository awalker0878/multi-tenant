<?php

declare(strict_types=1);

namespace App\Infrastructure\Catalogue;

use App\Application\IntentRevisions\Contracts\IntentValidator;
use App\Domain\IntentRevisions\IntentFailure;
use Opis\JsonSchema\Validator;

final class SchemaIntentValidator implements IntentValidator
{
    public function validate(array $intent): void
    {
        $json = json_encode($intent, JSON_THROW_ON_ERROR);
        if (strlen($json) > 262144) {
            throw new IntentFailure('intent_too_large', 413);
        }
        $schema = file_get_contents(resource_path('contracts/intent-v1.json'));
        if ($schema === false) {
            throw new IntentFailure('schema_unavailable', 503);
        }
        $result = (new Validator)->validate(json_decode($json), json_decode($schema));
        if (! $result->isValid()) {
            throw new IntentFailure('invalid_intent_schema');
        }
    }
}
