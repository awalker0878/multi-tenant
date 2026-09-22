"""Profile catalog loading.

Catalogs are reviewed JSON under `profiles/<family>/catalog.json`. The directory
is the only index: there is no second profile list to drift out of date.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from provisioner.domain.errors import ProvisioningError

ROOT = Path(__file__).resolve().parents[2]
PROFILE_ROOT = ROOT / 'profiles'

FAMILIES = ('environment', 'security', 'assurance', 'availability', 'recovery',
            'compute', 'storage', 'network', 'service', 'placement')

DEFERRED = 'DEFERRED_NOT_IMPLEMENTED'
STATUSES = ('IMPLEMENTED_INTERNAL_IPV4_OZ_RZ', DEFERRED)


@dataclass(frozen=True)
class Profile:
    family: str
    profile: str
    rank: int
    status: str
    description: str
    requires: dict = field(default_factory=dict)
    platform_inputs: dict = field(default_factory=dict)
    limits: tuple[str, ...] = ()

    @property
    def implemented(self) -> bool:
        return self.status != DEFERRED

    @property
    def trust(self) -> str | None:
        return self.requires.get('trust')

    @property
    def service_class(self) -> str | None:
        return self.requires.get('service_class')

    def to_dict(self) -> dict:
        return {'family': self.family, 'profile': self.profile, 'rank': self.rank,
                'status': self.status, 'description': self.description,
                'requires': dict(self.requires),
                'platform_inputs': dict(self.platform_inputs),
                'limits': list(self.limits)}


@dataclass(frozen=True)
class Catalog:
    families: dict[str, dict[str, Profile]]

    def get(self, family: str, profile: str) -> Profile:
        if family not in self.families:
            raise ProvisioningError('UNSUPPORTED_PROFILE', f'Unknown profile family: {family}',
                                    path=f'$.spec.{family}',
                                    details={'families': sorted(self.families)})
        if profile not in self.families[family]:
            raise ProvisioningError('UNSUPPORTED_PROFILE',
                                    f'Unknown {family} profile: {profile}',
                                    path=f'$.spec.{family}',
                                    details={'available': sorted(self.families[family])})
        return self.families[family][profile]

    def family(self, family: str) -> dict[str, Profile]:
        return self.families.get(family, {})

    def by_rank(self, family: str) -> list[Profile]:
        return sorted(self.family(family).values(), key=lambda p: (p.rank, p.profile))

    def names(self) -> dict[str, list[str]]:
        return {f: sorted(p) for f, p in sorted(self.families.items())}


def _load_one(path: Path) -> tuple[str, dict[str, Profile]]:
    family = path.parent.name
    try:
        document = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError) as exc:
        raise ProvisioningError('UNSUPPORTED_PROFILE', f'Unreadable profile catalog: {exc}',
                                path=str(path.relative_to(ROOT))) from exc
    if document.get('family') != family:
        raise ProvisioningError('UNSUPPORTED_PROFILE',
                                f'Catalog family {document.get("family")!r} does not match directory {family!r}',
                                path=str(path.relative_to(ROOT)))
    rows = document.get('profiles')
    if not isinstance(rows, list) or not rows:
        raise ProvisioningError('UNSUPPORTED_PROFILE', 'Empty profile catalog',
                                path=str(path.relative_to(ROOT)))
    profiles: dict[str, Profile] = {}
    ranks: set[tuple[str, int]] = set()
    allowed = {'profile', 'rank', 'status', 'description', 'requires', 'platform_inputs', 'limits'}
    for row in rows:
        if not isinstance(row, dict) or not {'profile', 'rank', 'status', 'description'} <= set(row):
            raise ProvisioningError('UNSUPPORTED_PROFILE', 'Incomplete profile entry',
                                    path=str(path.relative_to(ROOT)))
        if set(row) - allowed:
            raise ProvisioningError('UNSUPPORTED_PROFILE',
                                    f'Unknown profile entry field in {row.get("profile")}: {sorted(set(row) - allowed)}',
                                    path=str(path.relative_to(ROOT)))
        if row['status'] not in STATUSES:
            raise ProvisioningError('UNSUPPORTED_PROFILE', f'Unknown profile status: {row["status"]}',
                                    path=str(path.relative_to(ROOT)))
        rank_key = (row['profile'].split('/', 1)[0] if '/' in row['profile'] else family, row['rank'])
        if row['profile'] in profiles or rank_key in ranks:
            raise ProvisioningError('UNSUPPORTED_PROFILE', f'Duplicate profile or rank: {row["profile"]}',
                                    path=str(path.relative_to(ROOT)))
        profiles[row['profile']] = Profile(
            family=family, profile=row['profile'], rank=row['rank'], status=row['status'],
            description=row['description'], requires=dict(row.get('requires', {})),
            platform_inputs=dict(row.get('platform_inputs', {})),
            limits=tuple(row.get('limits', [])))
        ranks.add(rank_key)
    return family, profiles


def load_catalogs(root: Path = PROFILE_ROOT) -> Catalog:
    families: dict[str, dict[str, Profile]] = {}
    for path in sorted(root.glob('*/catalog.json')):
        family, profiles = _load_one(path)
        if family not in FAMILIES:
            raise ProvisioningError('UNSUPPORTED_PROFILE', f'Unknown profile family directory: {family}',
                                    path=str(path.relative_to(ROOT)))
        families[family] = profiles
    missing = [f for f in FAMILIES if f not in families]
    if missing:
        raise ProvisioningError('UNSUPPORTED_PROFILE', f'Missing profile catalogs: {missing}')
    return Catalog(families=families)