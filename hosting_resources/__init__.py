"""Reviewed runtime resources, independent of the process working directory.

Wheels own their data below this package, never at the shared site-packages
root. Source development uses the explicitly marked source tree. The resource
root is selected once; a missing installed resource cannot fall back to a
checkout or to another distribution's similarly named file.
"""
from __future__ import annotations

import atexit
import json
from contextlib import ExitStack
from importlib.resources import as_file, files
from pathlib import Path, PurePosixPath


# Runbooks shipped with application/control-plane runtime owners even when no
# capability index yet cites the new implementation. Build and integrity owners
# share this exact declaration; missing files cannot be repaired from a checkout.
_runtime_docs = json.loads(files(__name__).joinpath('runtime-documents.json').read_text(encoding='utf-8'))
if (not isinstance(_runtime_docs, list) or not _runtime_docs
        or any(not isinstance(name, str) or not name.startswith('docs/')
               or '..' in PurePosixPath(name).parts or '\\' in name or ':' in name
               or name != PurePosixPath(name).as_posix() for name in _runtime_docs)
        or len(_runtime_docs) != len(set(_runtime_docs))):
    raise ValueError('Invalid hosted runtime documentation manifest')
EXTRA_EVIDENCE_DOCS = tuple(_runtime_docs)


_resources = ExitStack()
atexit.register(_resources.close)
_package = files(__name__)
_bundled = _package.joinpath('_assets')
_source = Path(__file__).resolve().parents[1]
SOURCE_ROOT = (_source if (_source / '.hosting-root').is_file()
               and (_source / 'pyproject.toml').is_file() else None)

if _bundled.is_dir():
    # Keep an extracted resource tree alive for native tools that require paths.
    RESOURCE_ROOT = _resources.enter_context(as_file(_bundled))
elif SOURCE_ROOT is not None:
    RESOURCE_ROOT = SOURCE_ROOT
else:
    raise RuntimeError('The hosting runtime distribution has no bundled resources')


def resource_path(relative_path: str | Path) -> Path:
    """Resolve a normalized reviewed resource without a per-file fallback."""
    value = str(relative_path)
    path = PurePosixPath(value)
    if (not value or path.is_absolute() or value != path.as_posix()
            or '..' in path.parts or '\\' in value or ':' in value):
        raise ValueError(f'Unsafe runtime asset path: {relative_path}')
    target = RESOURCE_ROOT.joinpath(*path.parts)
    if not target.resolve().is_relative_to(RESOURCE_ROOT.resolve()):
        raise ValueError(f'Runtime asset escapes its resource root: {relative_path}')
    return target
