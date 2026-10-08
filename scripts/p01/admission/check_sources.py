"""Validate the artifact that binds an Actions job to its actual test merge."""
import hashlib
import io
import json
import zipfile

from policy import need


def validate_source(raw, artifact, run, job, expected, *, repository, name, head, base, tested, number):
    need(len(raw) <= 1024 * 1024 and artifact['digest'] == 'sha256:' + hashlib.sha256(raw).hexdigest(), 'check_artifact_digest_mismatch')
    need(not artifact['expired'] and run['event'] == 'pull_request' and run['head_sha'] == head,
         'check_run_not_current_pr')
    need(job['run_id'] == run['id'] and job['name'] == name and job['conclusion'] == 'success', 'check_job_mismatch')
    need(run['path'] == '.github/workflows/' + expected['workflow'], 'check_workflow_mismatch')
    need(artifact['name'] == f"check-source-{expected['job']}-{run['id']}-{run['run_attempt']}", 'check_attempt_mismatch')
    with zipfile.ZipFile(io.BytesIO(raw)) as package:
        need(package.namelist() == ['report.json'] and package.getinfo('report.json').file_size <= 65536,
             'invalid_check_artifact')
        record = json.loads(package.read('report.json'))
    need(record['result'] == 'PASSED' and record['source_revision'] == tested
         and record['pull_request'] == {'number': number, 'head': head, 'base': base}, 'check_source_mismatch')
    need(record['name'] == name and record['event'] == 'pull_request'
         and record['run_id'] == run['id'] and record['run_attempt'] == run['run_attempt']
         and record['job'] == expected['job'], 'check_record_identity_mismatch')
    need(record['workflow_ref'] == repository + '/.github/workflows/' + expected['workflow'] + f'@refs/pull/{number}/merge',
         'check_workflow_ref_mismatch')
    return record
