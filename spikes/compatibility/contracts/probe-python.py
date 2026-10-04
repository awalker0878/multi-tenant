"""Exercise generated private models without contacting any API."""
import json
import sys
from pathlib import Path
from pydantic import ValidationError

sys.path.insert(0, sys.argv[1])
from p00_private_client.models.sample import Sample
from p00_private_client.models.create_sample import CreateSample

fixtures = json.loads(Path(sys.argv[2]).read_text())
wire = next(x['value'] for x in fixtures if x['id'] == 'sample-valid')
model = Sample.from_dict(wire)
assert model is not None and model.to_dict() == wire
extended = dict(wire, future_display='synthetic')
assert Sample.from_dict(extended).to_dict() == extended
for key, value in [('phase', 'executing'), ('schema_version', 2), ('revision', 9007199254740993)]:
    try:
        Sample.from_dict(dict(wire, **{key: value}))
    except ValidationError:
        pass
    else:
        raise AssertionError(f'Generated Python model accepted invalid {key}')
# This is a measured generator limitation, not approval to accept this request.
# The authoritative OAS request validator separately rejects the same unknown key.
request = CreateSample.model_validate({'label': 'probe', 'actor_id': 'untrusted'})
assert 'actor_id' not in request.model_dump()
print(json.dumps({'status': 'PASS', 'round_trip': 'null and decimal-string precision preserved',
                  'negative_model_cases': 3, 'known_gap': 'generated request model ignores extra input keys'}))
