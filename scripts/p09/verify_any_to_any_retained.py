"""Verify retained local evidence without promoting skips to native qualification."""
import hashlib
import io
import json
import re
import subprocess
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / 'verification/p09/any-to-any-local'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git(root: Path, *args: str) -> str:
    return subprocess.check_output(['git', *args], cwd=root, text=True, stderr=subprocess.PIPE).strip()


def object_id(value: object) -> str:
    if not isinstance(value, str) or not re.fullmatch('[0-9a-f]{40}', value):
        raise ValueError('invalid_source_history_object_id')
    return value


@contextmanager
def source_object_store(root: Path, evidence: Path, sources: set[str]) -> Iterator[Path]:
    """Read original commits from a verified bundle without changing the checkout."""
    manifest_path = evidence / 'source-history.json'
    if not manifest_path.exists():
        for source in sources:
            git(root, 'cat-file', '-e', object_id(source) + '^{commit}')
        yield root
        return
    manifest = json.loads(manifest_path.read_text())
    if manifest.get('schema_version') != 1 or manifest.get('archive') != 'source-history.bundle':
        raise ValueError('invalid_source_history_manifest')
    archive = evidence / 'source-history.bundle'
    if archive.is_symlink() or sha(archive) != manifest.get('archive_sha256'):
        raise ValueError('source_history_archive_digest_mismatch')
    prerequisite = object_id(manifest.get('prerequisite_commit'))
    head = object_id(manifest.get('archived_head'))
    head_tree = object_id(manifest.get('archived_head_tree'))
    commits = manifest.get('commits')
    if not isinstance(commits, dict) or not sources.issubset(commits):
        raise ValueError('source_history_report_revision_missing')
    for revision, tree in commits.items():
        object_id(revision)
        object_id(tree)
    # The published branch retains the audit baseline as its ancestor. Its
    # object store supplies the bundle prerequisite, not historical results.
    try:
        git(root, 'cat-file', '-e', prerequisite + '^{commit}')
    except subprocess.CalledProcessError as error:
        raise ValueError(
            'source_history_prerequisite_missing: fetch the full audit baseline history '
            '(actions/checkout fetch-depth: 0)'
        ) from error
    objects = Path(git(root, 'rev-parse', '--git-path', 'objects'))
    if not objects.is_absolute():
        objects = root / objects
    with tempfile.TemporaryDirectory(prefix='p09-source-history-') as directory:
        private = Path(directory)
        git(private, 'init', '--bare', '--quiet', '.')
        (private / 'objects/info/alternates').write_text(str(objects.resolve()) + '\n')
        # The archive begins at the audit baseline; older ancestors are outside
        # its scope and need not exist in a shallow published checkout.
        (private / 'shallow').write_text(prerequisite + '\n')
        git(private, 'update-ref', 'refs/prerequisites/audit-baseline', prerequisite)
        git(private, 'bundle', 'verify', str(archive.resolve()))
        heads = git(private, 'bundle', 'list-heads', str(archive.resolve())).splitlines()
        if not any(line.split()[0] == head for line in heads):
            raise ValueError('source_history_archived_head_missing')
        git(private, 'bundle', 'unbundle', str(archive.resolve()))
        if git(private, 'rev-parse', head + '^{tree}') != head_tree:
            raise ValueError('source_history_archived_tree_mismatch')
        git(private, 'merge-base', '--is-ancestor', prerequisite, head)
        for revision, tree in commits.items():
            if git(private, 'rev-parse', revision + '^{tree}') != tree:
                raise ValueError('source_history_commit_tree_mismatch')
            git(private, 'merge-base', '--is-ancestor', prerequisite, revision)
            git(private, 'merge-base', '--is-ancestor', revision, head)
        yield private


def verify_retained(root: Path = ROOT, evidence: Path = EVIDENCE) -> None:
    index = json.loads((evidence / 'qualification-index.json').read_text())
    for name, expected in index['artifact_sha256'].items():
        assert sha(evidence / name) == expected, name
    reports = [(path, json.loads(path.read_text())) for path in evidence.rglob('report.json')]
    sources = {report['source_revision'] for _, report in reports if report.get('source_bindings')}
    with source_object_store(root, evidence, sources) as source_root:
        for path, report in reports:
            for command in report.get('commands', []):
                assert sha(path.parent / command['log']) == command['sha256'], path
            for name, expected in report.get('artifact_sha256', {}).items():
                assert sha(path.parent / name) == expected, name
            bindings = report.get('source_bindings', {})
            if bindings:
                source = report['source_revision']
                raw = subprocess.check_output(['git', 'cat-file', '--batch'], cwd=source_root,
                    input=''.join(source + ':' + name + '\n' for name in bindings).encode())
                stream = io.BytesIO(raw)
                for name, expected in bindings.items():
                    header = stream.readline().decode().split()
                    assert header[1] == 'blob', name
                    data = stream.read(int(header[2]))
                    assert stream.read(1) == b'\n'
                    assert hashlib.sha256(data).hexdigest() == expected, (source, name)
    component = json.loads((evidence / 'components/report.json').read_text())
    assert all(row['result'] != 'FAILED' for row in component['suites'])
    assert sum(row['suite']['tests'] - row['suite']['skipped'] for row in component['suites']) == 1637
    assert sum(row['suite']['skipped'] for row in component['suites']) == 146
    assert all(row['suite']['failures'] == row['suite']['errors'] == 0 for row in component['suites'])
    browser = json.loads((evidence / 'browser/report.json').read_text())
    assert browser['result'] == 'PASSED' and browser['stats']['expected'] == 9
    assert all(browser['stats'][key] == 0 for key in ('unexpected', 'flaky', 'skipped'))
    assert index['full_qualification'] == 'not_established'
    print('Verified 1,637 passing component tests, 146 explicit database skips, nine browser journeys, historical source/log/artifact hashes and original failures. Native qualification remains unestablished.')


if __name__ == '__main__':
    verify_retained()
