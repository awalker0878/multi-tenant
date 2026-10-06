<?php

declare(strict_types=1);

namespace App\Infrastructure\Catalogue;

use App\Application\IntentRevisions\Contracts\IntentValidator;
use App\Domain\IntentRevisions\IntentFailure;
use Opis\JsonSchema\Errors\ErrorFormatter;
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

            $error = $result->error();
            $fields = $error === null ? [] : (new ErrorFormatter)->format($error, false, fn () => 'invalid');
            $first = array_key_first($fields);
            $field = is_string($first) ? str_replace('/', '.', trim($first, '/')) : 'intent';
            throw new IntentFailure('invalid_intent_schema', 422, $field !== '' && preg_match('/\A[a-zA-Z0-9_.]{1,200}\z/', $field) ? $field : 'intent');
        }
    }
}
