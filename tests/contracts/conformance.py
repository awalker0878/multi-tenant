"""Compare actual PHP/Python schema acceptance and canonical digest golden vectors."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

from planning.infrastructure.messaging.codec import canonical, decode

root = Path(__file__).resolve().parents[2]
parser = argparse.ArgumentParser()
parser.add_argument('--php', default='php')
args = parser.parse_args()
fixtures = json.loads((root/'tests/contracts/fixtures.json').read_text())
python = []
for fixture in fixtures:
    try:
        event = decode(json.dumps(fixture['value']).encode())
        python.append({'id':fixture['id'], 'valid':True, 'sha256':hashlib.sha256(canonical(event)).hexdigest()})
    except Exception:
        python.append({'id':fixture['id'], 'valid':False})
php = json.loads(subprocess.run([args.php, str(root/'tests/contracts/php.php'),str(root/'services/catalogue'),str(root/'tests/contracts/fixtures.json')],check=True,capture_output=True,timeout=30).stdout)
assert php == python, (php, python)
assert [x['valid'] for x in python] == [x['valid'] for x in fixtures]
print(json.dumps({'result':'PASS','fixtures':len(fixtures),'cross_language':python},indent=2))
