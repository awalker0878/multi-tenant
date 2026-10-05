"""Download reviewed exact tool bytes; no install scripts or mutable latest tags."""
import hashlib
import json
from pathlib import Path
import tarfile
import urllib.request


def install(root: Path, destination: Path) -> dict[str, str]:
    lock = json.loads((root / 'release/artifact-tools.lock.json').read_text())
    destination.mkdir(parents=True, exist_ok=True)
    result = {}
    for name in ('cosign', 'trivy'):
        item = lock[name]
        archive = destination / (name + '.download')
        with urllib.request.urlopen(item['url'], timeout=60) as response, archive.open('wb') as out:
            total = 0
            while chunk := response.read(1024 * 1024):
                total += len(chunk)
                if total > 256 * 1024 * 1024:
                    raise ValueError('tool_download_too_large')
                out.write(chunk)
        with archive.open('rb') as stream:
            observed = hashlib.file_digest(stream, 'sha256').hexdigest()
        if observed != item['sha256']:
            raise ValueError('tool_digest_mismatch')
        target = destination / name
        if item['archive']:
            with tarfile.open(archive) as package:
                member = package.getmember(name)
                if not member.isfile() or member.size > 256 * 1024 * 1024:
                    raise ValueError('unsafe_tool_member')
                target.write_bytes(package.extractfile(member).read())
            archive.unlink()
        else:
            archive.rename(target)
        target.chmod(0o700)
        result[name] = str(target)
    return result


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(install(Path(__file__).resolve().parents[3], args.output)))
